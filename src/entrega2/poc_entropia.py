"""Prueba de concepto: cómo responde cada configuración cuando el corpus mezcla versiones.

El corpus tiene dos versiones del programa del curso (2020-20 y 2026-20) que se
contradicen en varias reglas. Las preguntas de data/bronce/evaluacion/preguntas_vigencia.json
tienen una respuesta vigente y una desactualizada; cada configuración las responde
y un juez clasifica con cuál de las dos coincide.

    python3 src/entrega2/poc_entropia.py [--rehacer]
"""

import argparse
import json
from collections import Counter

from base_vectorial import conectar
from catalogo import cargar_catalogo
from config import DIR_RESULTADOS, MODELO_JUEZ, PREGUNTAS
from enfoques import Resultado, documentos_completos, responder_directo, responder_rag
from evaluar import guardar_json, leer_json
from llm import cliente, generar

PREGUNTAS_DE_VIGENCIA = PREGUNTAS.with_name('preguntas_vigencia.json')
ARCHIVO = DIR_RESULTADOS / 'entropia' / 'poc.json'

# nombre: (colección, solo_vigentes, con_vigencia). Las dos primeras no usan ninguna
# etiqueta del catálogo: son el RAG tal como queda al indexar una carpeta de PDF.
CONFIGURACIONES_RAG = {
    'rag_ingenuo_texto': ('texto', False, False),
    'rag_ingenuo_visual': ('visual', False, False),
    'rag_con_etiquetas': ('visual', False, True),
    'rag_filtro_vigente': ('visual', True, True),
}
DIRECTO = 'directo_dos_programas'
CONFIGURACIONES = (*CONFIGURACIONES_RAG, DIRECTO)

CLASES = ('vigente', 'desactualizada', 'ambas_distinguiendo', 'ambas_sin_distinguir', 'abstencion')

INSTRUCCIONES_JUEZ = """Clasificas la respuesta de un asistente a una pregunta cuya respuesta cambió entre dos versiones de un documento.

- vigente: la respuesta coincide con la respuesta vigente y no presenta la desactualizada como cierta.
- desactualizada: la respuesta da como cierta la respuesta desactualizada, sin advertir que es de una versión anterior.
- ambas_distinguiendo: menciona las dos y deja claro cuál es la vigente.
- ambas_sin_distinguir: menciona las dos sin decir cuál aplica hoy, o las mezcla.
- abstencion: dice que no hay información suficiente."""

FORMATO_JUEZ = {'format': {
    'type': 'json_schema', 'name': 'clasificacion', 'strict': True,
    'schema': {
        'type': 'object',
        'properties': {'clase': {'type': 'string', 'enum': list(CLASES)}, 'motivo': {'type': 'string'}},
        'required': ['clase', 'motivo'], 'additionalProperties': False,
    },
}}


def _clasificar(api, pregunta: dict, respuesta: str) -> dict:
    caso = json.dumps({**pregunta, 'respuesta_del_asistente': respuesta}, ensure_ascii=False, indent=2)
    return json.loads(generar(api, INSTRUCCIONES_JUEZ, caso, modelo=MODELO_JUEZ, text=FORMATO_JUEZ).texto)


def ejecutar() -> dict:
    preguntas = leer_json(PREGUNTAS_DE_VIGENCIA, [])
    resultados = leer_json(ARCHIVO, {})
    api = cliente()
    programas = documentos_completos([doc for doc in cargar_catalogo() if doc.tipo == 'programa'])
    with conectar() as conexion:
        for pregunta in preguntas:
            for configuracion in CONFIGURACIONES:
                clave = f"{pregunta['id']}|{configuracion}"
                if clave in resultados:
                    continue
                if configuracion == DIRECTO:
                    resultado: Resultado = responder_directo(api, pregunta['pregunta'], programas)
                else:
                    coleccion, solo_vigentes, con_vigencia = CONFIGURACIONES_RAG[configuracion]
                    resultado = responder_rag(
                        api, conexion, pregunta['pregunta'],
                        coleccion=coleccion, solo_vigentes=solo_vigentes, con_vigencia=con_vigencia,
                    )
                resultados[clave] = {
                    'respuesta': resultado.respuesta, 'fuentes': resultado.fuentes, 'uso': resultado.uso,
                    **_clasificar(api, pregunta, resultado.respuesta),
                }
                guardar_json(ARCHIVO, resultados)
    return resultados


def imprimir(resultados: dict) -> None:
    preguntas = leer_json(PREGUNTAS_DE_VIGENCIA, [])
    print(f'{"":<8}' + ''.join(f'{configuracion:>24}' for configuracion in CONFIGURACIONES))
    for pregunta in preguntas:
        clases = [resultados[f"{pregunta['id']}|{configuracion}"]['clase'] for configuracion in CONFIGURACIONES]
        print(f"{pregunta['id']:<8}" + ''.join(f'{clase:>24}' for clase in clases))
    for configuracion in CONFIGURACIONES:
        conteo = Counter(resultados[f"{p['id']}|{configuracion}"]['clase'] for p in preguntas)
        print(f'{configuracion}: {dict(conteo)}')


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumentos.add_argument('--rehacer', action='store_true', help='descarta los resultados guardados')
    if argumentos.parse_args().rehacer:
        ARCHIVO.unlink(missing_ok=True)
    imprimir(ejecutar())


if __name__ == '__main__':
    main()
