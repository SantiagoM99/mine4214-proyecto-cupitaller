"""Preparar las tutorías de un día: qué temas trabajar con cada estudiante que reservó.

Requerimiento que justifica la arquitectura híbrida. Para cada reserva del día cruza:
  bodega (Silver)  para qué reservó (encuesta previa) y qué dijo en sus encuestas anteriores
  documentos       los contenidos del curso hasta el nivel en que va el curso esta semana
y un modelo propone los temas, sin salirse de lo que el estudiante ya vio.

Los comentarios de las encuestas son texto libre que puede identificar a estudiantes y
tutores, así que todo corre en el equipo: embeddings e5, Postgres local y Qwen3 en
Ollama. El agente de OpenAI sigue sin ver texto libre. La salida con datos reales se
escribe en artifacts/entrega2/privado/, que no se versiona, y por consola solo salen
métricas agregadas.

La bodega no registra en qué nivel va el curso: lo indica el monitor (--nivel).

    python3 src/entrega2/tutorias_del_dia.py --demo                     # estudiante ficticio
    python3 src/entrega2/tutorias_del_dia.py --fecha 2026-02-09 --nivel 1
"""

import argparse
import csv
import json
import statistics
import time
from collections import defaultdict

from agente import listar_presentaciones
from base_vectorial import buscar, conectar
from config import ARTIFACTS, DATA, DIR_RESULTADOS, MODELO_LOCAL, PERIODO_VIGENTE, SILVER_RESERVAS
from enfoques import contexto_de_fragmentos
from llm import cliente_local, generar

DIR_PRIVADO = ARTIFACTS / 'privado'
ARCHIVO_DEMO = DIR_RESULTADOS / 'experimentos' / 'tutorias_demo.json'
SERVICIO_IP = 'ISIS-1221'
ESTADOS_ATENDIDOS = {'Finalizada', 'Realizada', 'No asistió', 'En ejecución'}
ENCUESTAS_ANTERIORES = 5
FRAGMENTOS = 5

PROPOSITO = 'pregunta_e70905bd9b1c'  # encuesta previa: «La mayoría del tiempo de la tutoría que estoy reservando lo usaré para»
CAMPOS_SATISFACCION = {
    'pregunta_8644ad182746': 'en qué usó la tutoría',
    'pregunta_5a7441428672': 'comprensión del tema actual (1 a 5)',
    'pregunta_16932259e848': 'comentario sobre el curso y sus contenidos',
    'pregunta_bfe0495fc3c0': 'comentario sobre el tutor y la tutoría',
    'pregunta_3bcd7ccbdb47': 'sugerencias',
}

INSTRUCCIONES = """Ayudas a un monitor de CupiTaller (tutorías del curso Introducción a la Programación) a preparar la tutoría con un estudiante.

Recibes:
- el nivel en que va el curso y las presentaciones vistas hasta ese nivel (lo que el estudiante ya debería conocer);
- para qué reservó el estudiante y lo que escribió en encuestas de tutorías anteriores;
- pasajes del material del curso relacionados.

Propón de 1 a 3 temas para la tutoría. Reglas:
1. Cada tema debe corresponder a una presentación de la lista, copiando su título exacto, y a un nivel menor o igual al del curso.
2. Si el estudiante pide o menciona algo que el curso todavía no ha visto, no lo propongas como tema: anótalo en fuera_de_nivel y propón en su lugar lo que sí corresponde al nivel.
3. Justifica cada tema con lo que dijo el estudiante o con el propósito de la reserva. No inventes dificultades que no aparezcan.
4. Si no hay historia del estudiante, básate en el propósito de la reserva y en los temas del nivel actual.
5. Escribe en español, con frases cortas. No repitas nombres de personas que aparezcan en los comentarios."""

FORMATO = {'format': {
    'type': 'json_schema', 'name': 'preparacion', 'strict': True,
    'schema': {
        'type': 'object',
        'properties': {
            'resumen': {'type': 'string', 'description': 'Una frase sobre qué necesita el estudiante.'},
            'temas': {'type': 'array', 'items': {
                'type': 'object',
                'properties': {'tema': {'type': 'string'}, 'presentacion': {'type': 'string'},
                               'nivel': {'type': 'integer'}, 'motivo': {'type': 'string'}},
                'required': ['tema', 'presentacion', 'nivel', 'motivo'], 'additionalProperties': False}},
            'fuera_de_nivel': {'type': 'array', 'items': {'type': 'string'}},
            'pregunta_para_empezar': {'type': 'string'},
        },
        'required': ['resumen', 'temas', 'fuera_de_nivel', 'pregunta_para_empezar'], 'additionalProperties': False,
    },
}}

DEMO = [{
    'estudiante': 'Pepito (ficticio)',
    'proposito': 'Desarrollar un ejercicio en senecode',
    'historia': [
        {'en qué usó la tutoría': 'Resolver dudas puntuales de los conceptos de la clase', 'comprensión del tema actual (1 a 5)': '2',
         'comentario sobre el curso y sus contenidos': 'Me confundo cuando hay varios if seguidos y no sé cuándo usar elif.'},
        {'en qué usó la tutoría': 'Desarrollar un laboratorio', 'comprensión del tema actual (1 a 5)': '3',
         'comentario sobre el tutor y la tutoría': 'El tutor me mostró un ciclo for para contar letras pero no lo entendí.',
         'sugerencias': 'Más ejercicios de contar cosas dentro de un texto.'},
    ],
}]


def contenidos_hasta(nivel: int) -> dict[int, list[str]]:
    return {n: listar_presentaciones(PERIODO_VIGENTE, n)['presentaciones'] for n in range(1, nivel + 1)}


def _leer_csv(nombre: str) -> list[dict]:
    with (DATA / 'plata' / f'{nombre}.csv').open(encoding='utf-8') as entrada:
        return list(csv.DictReader(entrada))


def estudiantes_del_dia(fecha: str) -> list[dict]:
    """Una entrada por estudiante con reserva de IP ese día, con un seudónimo en lugar del código."""
    with SILVER_RESERVAS.open(encoding='utf-8') as entrada:
        del_dia = [r for r in csv.DictReader(entrada)
                   if r['fecha_inicio'][:10] == fecha and r['codigo_servicio'] == SERVICIO_IP and r['estado_reserva'] in ESTADOS_ATENDIDOS]
    proposito = {e['id_reserva']: e[PROPOSITO] for e in _leer_csv('encuesta_previa_normal_ip')}
    anteriores = defaultdict(list)
    for nombre in ('encuesta_satisfaccion_normal', 'encuesta_satisfaccion_express'):
        for e in _leer_csv(nombre):
            if e['fecha_inicio'][:10] < fecha:
                anteriores[e['codigo_usuario']].append(e)
    estudiantes, vistos = [], set()
    for reserva in sorted(del_dia, key=lambda r: r['fecha_inicio']):
        if reserva['codigo_usuario'] in vistos:
            continue
        vistos.add(reserva['codigo_usuario'])
        recientes = sorted(anteriores[reserva['codigo_usuario']], key=lambda e: e['fecha_inicio'])[-ENCUESTAS_ANTERIORES:]
        historia = [{etiqueta: e[campo] for campo, etiqueta in CAMPOS_SATISFACCION.items() if e.get(campo, '').strip()}
                    for e in recientes]
        estudiantes.append({
            'estudiante': f'Estudiante {len(estudiantes) + 1}', 'hora': reserva['fecha_inicio'][11:16],
            'proposito': proposito.get(reserva['id_reserva'], 'sin encuesta previa'),
            'historia': [h for h in historia if h],
        })
    return estudiantes


def _consulta(estudiante: dict) -> str:
    textos = [estudiante['proposito']] + [v for h in estudiante['historia'] for k, v in h.items() if k.startswith('comentario') or k == 'sugerencias']
    return ' '.join(textos)[:1500]


def preparar(api, conexion, estudiante: dict, nivel: int, contenidos: dict[int, list[str]]) -> dict:
    inicio = time.perf_counter()
    candidatos = buscar(conexion, _consulta(estudiante), coleccion='visual', k=30, solo_vigentes=True)
    pasajes = [f for f in candidatos if f.nivel is None or f.nivel <= nivel][:FRAGMENTOS]
    temario = '\n'.join(f'Nivel {n}: ' + '; '.join(titulos) for n, titulos in contenidos.items())
    entrada = (f'El curso va en el Nivel {nivel}. Presentaciones vistas hasta ahora:\n{temario}\n\n'
               f'Propósito de la reserva: {estudiante["proposito"]}\n\n'
               f'Encuestas anteriores del estudiante (de la más antigua a la más reciente):\n'
               f'{json.dumps(estudiante["historia"], ensure_ascii=False, indent=1) if estudiante["historia"] else "ninguna"}\n\n'
               f'Pasajes del material:\n{contexto_de_fragmentos(pasajes, con_vigencia=False)}')
    respuesta = generar(api, INSTRUCCIONES, entrada, modelo=MODELO_LOCAL, text=FORMATO)
    propuesta = json.loads(respuesta.texto)
    permitidas = {titulo for titulos in contenidos.values() for titulo in titulos}
    return {
        **estudiante, 'propuesta': propuesta,
        'pasajes': [f.origen for f in pasajes],
        'temas_dentro_del_nivel': sum(t['presentacion'] in permitidas for t in propuesta['temas']),
        'temas_propuestos': len(propuesta['temas']),
        'segundos': round(time.perf_counter() - inicio, 1),
    }


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumentos.add_argument('--demo', action='store_true', help='estudiante ficticio; la salida se puede versionar')
    argumentos.add_argument('--fecha', default='2026-02-09')
    argumentos.add_argument('--nivel', type=int, default=2)
    a = argumentos.parse_args()
    estudiantes = DEMO if a.demo else estudiantes_del_dia(a.fecha)
    contenidos = contenidos_hasta(a.nivel)
    api = cliente_local()
    with conectar() as conexion:
        preparaciones = [preparar(api, conexion, e, a.nivel, contenidos) for e in estudiantes]
    salida = ARCHIVO_DEMO if a.demo else DIR_PRIVADO / f'tutorias_{a.fecha}_nivel{a.nivel}.json'
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps({'fecha': a.fecha, 'nivel': a.nivel, 'modelo': MODELO_LOCAL, 'preparaciones': preparaciones},
                                 ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    metricas = {
        'estudiantes': len(preparaciones),
        'con_historia': sum(bool(p['historia']) for p in preparaciones),
        'temas_propuestos': sum(p['temas_propuestos'] for p in preparaciones),
        'temas_dentro_del_nivel': sum(p['temas_dentro_del_nivel'] for p in preparaciones),
        'estudiantes_con_algo_fuera_de_nivel': sum(bool(p['propuesta']['fuera_de_nivel']) for p in preparaciones),
        'segundos_mediana': statistics.median(p['segundos'] for p in preparaciones),
        'segundos_total': round(sum(p['segundos'] for p in preparaciones), 1),
        'salida': str(salida),
    }
    print(json.dumps(metricas, ensure_ascii=False, indent=2))
    if not a.demo:
        (DIR_RESULTADOS / 'experimentos' / f'tutorias_{a.fecha}_metricas.json').write_text(
            json.dumps({k: v for k, v in metricas.items() if k != 'salida'} | {'fecha': a.fecha, 'nivel': a.nivel, 'modelo': MODELO_LOCAL},
                       ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
