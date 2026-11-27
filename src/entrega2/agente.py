"""Agente híbrido: contrasta lo que dicen los documentos con lo que registra la bodega.

El modelo decide qué herramienta usar en cada paso: `buscar_documentos` consulta la
base vectorial (RAG), `listar_presentaciones` lee del catálogo qué presentaciones hay
de un semestre y un nivel, y `consultar_bodega` ejecuta SQL de solo lectura sobre el
modelo dimensional de la Entrega 1.

    python3 src/entrega2/agente.py "¿Qué tipos de tutoría ofrece CupiTaller y cuáles se usan hoy?"
"""

import argparse
import json
from dataclasses import dataclass, field

import psycopg
from openai import OpenAI

from base_vectorial import buscar, conectar
from bodega import consultar, descripcion
from catalogo import cargar_catalogo
from enfoques import contexto_de_fragmentos
from config import MODELO_LLM
from llm import cliente, generar

MAX_PASOS = 8
FRAGMENTOS_POR_BUSQUEDA = 5
# Del catálogo; el material viejo no es el curso completo (12 presentaciones de 2020-20 y 2021-10).
SEMESTRES_CON_PRESENTACIONES = ['2020-20', '2021-10', '2026-20']

INSTRUCCIONES = """Eres el analista de CupiTaller, el centro de tutorías del curso Introducción a la Programación (IP) de la Universidad de los Andes. Apoyas a la coordinación: respondes contrastando lo que establecen los documentos del curso con lo que ocurrió según la bodega de datos.

Herramientas:
- buscar_documentos: programas del curso y presentaciones de clase, de varios semestres. Cada resultado indica su semestre y si está vigente.
- listar_presentaciones: títulos de las presentaciones de un semestre y un nivel, en orden de clase. Sirve para saber qué temas tiene un nivel; la búsqueda solo trae pasajes sueltos.
- consultar_bodega: SQL (SQLite, solo SELECT) sobre la bodega descrita abajo.

Cómo trabajar:
1. Si la pregunta menciona una regla, una política o un contenido del curso, búscalo en los documentos. Si aparecen versiones de semestres distintos, identifica cuál está vigente y qué cambió.
2. Si la pregunta compara versiones del curso (qué cambió en un nivel), lista las presentaciones de ese nivel en cada semestre y usa buscar_documentos en el semestre viejo para comprobar los temas que solo aparezcan en la lista nueva: un título distinto no prueba que el tema falte, puede estar dentro de otra presentación. Advierte que del material viejo no se tiene el curso completo.
3. Si la pregunta se puede comprobar con datos, consulta la bodega. Escribe consultas agregadas (GROUP BY) en lugar de traer filas sueltas, y corrige la consulta si devuelve un error.
4. No afirmes nada que no venga de una herramienta. Si los documentos o la bodega no alcanzan para responder, dilo.

Respuesta final, en español y en prosa breve:
- Lo que dice el documento, citado como [título, semestre, p. N] e indicando si está vigente.
- Lo que muestra la bodega, con las cifras y la vista o tabla consultada.
- La conclusión: si la operación coincide con el documento, lo contradice, o el documento está desactualizado.
- Una limitación de los datos si afecta la conclusión.

"""

HERRAMIENTAS = [
    {
        'type': 'function',
        'name': 'buscar_documentos',
        'description': 'Busca pasajes en los programas del curso y las presentaciones de clase por similitud semántica.',
        'strict': True,
        'parameters': {
            'type': 'object',
            'properties': {
                'consulta': {'type': 'string', 'description': 'Lo que se busca, redactado como frase o pregunta.'},
                'solo_vigentes': {
                    'type': 'boolean',
                    'description': 'true limita la búsqueda a los documentos del semestre vigente; false incluye las versiones anteriores.',
                },
                'semestre': {
                    'type': 'string', 'enum': ['todos', *SEMESTRES_CON_PRESENTACIONES],
                    'description': 'Un semestre para buscar solo en sus documentos, o «todos».',
                },
            },
            'required': ['consulta', 'solo_vigentes', 'semestre'],
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'listar_presentaciones',
        'description': 'Lista, en orden de clase, los títulos de las presentaciones de un semestre y un nivel del curso.',
        'strict': True,
        'parameters': {
            'type': 'object',
            'properties': {
                'semestre': {'type': 'string', 'enum': SEMESTRES_CON_PRESENTACIONES},
                'nivel': {'type': 'integer', 'enum': [1, 2, 3, 4]},
            },
            'required': ['semestre', 'nivel'],
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'consultar_bodega',
        'description': 'Ejecuta una sentencia SELECT de SQLite sobre la bodega de CupiTaller y devuelve columnas y filas.',
        'strict': True,
        'parameters': {
            'type': 'object',
            'properties': {'sql': {'type': 'string', 'description': 'Una sola sentencia SELECT.'}},
            'required': ['sql'],
            'additionalProperties': False,
        },
    },
]


@dataclass
class Paso:
    herramienta: str
    argumentos: dict
    resultado: str


@dataclass
class RespuestaAgente:
    respuesta: str
    pasos: list[Paso] = field(default_factory=list)
    uso: dict[str, float] = field(default_factory=dict)


def _ejecutar(conexion: psycopg.Connection, herramienta: str, argumentos: dict) -> str:
    if herramienta == 'buscar_documentos':
        fragmentos = buscar(
            conexion, argumentos['consulta'], coleccion='visual',
            k=FRAGMENTOS_POR_BUSQUEDA, solo_vigentes=argumentos['solo_vigentes'],
            semestre=None if argumentos['semestre'] == 'todos' else argumentos['semestre'],
        )
        return contexto_de_fragmentos(fragmentos, con_vigencia=True)
    if herramienta == 'listar_presentaciones':
        return json.dumps(listar_presentaciones(argumentos['semestre'], argumentos['nivel']), ensure_ascii=False)
    return json.dumps(consultar(argumentos['sql']), ensure_ascii=False)


def listar_presentaciones(semestre: str, nivel: int) -> dict:
    documentos = sorted((d for d in cargar_catalogo() if d.tipo == 'presentacion' and d.periodo == semestre and d.nivel == nivel),
                        key=lambda d: d.orden or 0)
    return {'semestre': semestre, 'nivel': nivel, 'vigente': any(d.vigente for d in documentos),
            'presentaciones': [d.titulo for d in documentos]}


def _acumular(total: dict[str, float], uso: dict[str, float]) -> None:
    for clave, valor in uso.items():
        total[clave] = round(total.get(clave, 0) + valor, 2)


def preguntar(api: OpenAI, conexion: psycopg.Connection, pregunta: str, modelo: str = MODELO_LLM) -> RespuestaAgente:
    instrucciones = INSTRUCCIONES + descripcion()
    conversacion: list = [{'role': 'user', 'content': pregunta}]
    resultado = RespuestaAgente(respuesta='')
    for _ in range(MAX_PASOS):
        turno = generar(api, instrucciones, conversacion, modelo=modelo, tools=HERRAMIENTAS)
        _acumular(resultado.uso, turno.uso)
        llamadas = [item for item in turno.crudo.output if item.type == 'function_call']
        if not llamadas:
            resultado.respuesta = turno.texto
            return resultado
        conversacion += turno.crudo.output
        for llamada in llamadas:
            argumentos = json.loads(llamada.arguments)
            salida = _ejecutar(conexion, llamada.name, argumentos)
            resultado.pasos.append(Paso(llamada.name, argumentos, salida))
            conversacion.append({'type': 'function_call_output', 'call_id': llamada.call_id, 'output': salida})
    resultado.respuesta = f'El agente no llegó a una respuesta en {MAX_PASOS} pasos.'
    return resultado


def imprimir(resultado: RespuestaAgente) -> None:
    for numero, paso in enumerate(resultado.pasos, start=1):
        argumento = (paso.argumentos.get('sql') or paso.argumentos.get('consulta', '')
                     + (f" (solo vigentes: {paso.argumentos['solo_vigentes']})" if 'solo_vigentes' in paso.argumentos else '')
                     or f"{paso.argumentos['semestre']}, nivel {paso.argumentos['nivel']}")
        print(f'[{numero}] {paso.herramienta}: {argumento}')
        print(f'    → {paso.resultado[:300].replace(chr(10), " ")}{"…" if len(paso.resultado) > 300 else ""}')
    print(f'\n{resultado.respuesta}\n\n{resultado.uso}')


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumentos.add_argument('pregunta')
    pregunta = argumentos.parse_args().pregunta
    with conectar() as conexion:
        imprimir(preguntar(cliente(), conexion, pregunta))


if __name__ == '__main__':
    main()
