"""Reservas de un día y temas que cada estudiante mencionó antes: la fuente del agente para R3.

Los comentarios de las encuestas son texto libre que puede identificar a estudiantes y
tutores. Solo los lee el modelo local (Qwen3 en Ollama). Al agente le llegan un
seudónimo, la hora, el propósito de la reserva (una de siete opciones de la encuesta
previa) y los temas del curso que el modelo local encuentra en los comentarios.
"""

import csv
import json
import statistics
from collections import defaultdict
from functools import cache

from config import DATA, MODELO_LOCAL, SILVER_RESERVAS
from llm import cliente_local, generar

SERVICIO_IP = 'ISIS-1221'
ESTADOS_ATENDIDOS = {'Finalizada', 'Realizada', 'No asistió', 'En ejecución'}
ENCUESTAS_ANTERIORES = 5

PROPOSITO = 'pregunta_e70905bd9b1c'  # encuesta previa: «La mayoría del tiempo de la tutoría que estoy reservando lo usaré para»
COMPRENSION = 'pregunta_5a7441428672'  # encuesta de satisfacción: comprensión del tema actual, de 1 a 5
COMENTARIOS = ('pregunta_8644ad182746', 'pregunta_16932259e848', 'pregunta_bfe0495fc3c0', 'pregunta_3bcd7ccbdb47')

FECHA_DEMO = '2026-11-30'
DEMO = [{
    'estudiante': 'Pepito', 'hora': '10:00', 'proposito': 'Desarrollar un ejercicio en senecode',
    'comprension': ['2', '3'],
    'comentarios': ['Me confundo cuando hay varios if seguidos y no sé cuándo usar elif.',
                    'El tutor me mostró un ciclo for para contar letras pero no lo entendí.',
                    'Más ejercicios de contar cosas dentro de un texto.'],
}]

INSTRUCCIONES_TEMAS = """Lees comentarios que un estudiante de Introducción a la Programación (Python) escribió en encuestas de tutorías anteriores.
Devuelve solo los conceptos de programación con los que dice tener dificultad o que pide repasar, como nombres cortos de temas (por ejemplo «condicionales anidados», «ciclo for sobre strings»).
No copies frases del estudiante, no incluyas nombres de personas ni opiniones sobre el tutor. Si no menciona ningún concepto, devuelve una lista vacía."""

FORMATO_TEMAS = {'format': {
    'type': 'json_schema', 'name': 'temas', 'strict': True,
    'schema': {'type': 'object', 'properties': {'temas': {'type': 'array', 'items': {'type': 'string'}}},
               'required': ['temas'], 'additionalProperties': False},
}}


def _leer_plata(nombre: str) -> list[dict]:
    with (DATA / 'plata' / f'{nombre}.csv').open(encoding='utf-8') as entrada:
        return list(csv.DictReader(entrada))


@cache
def estudiantes_del_dia(fecha: str) -> tuple[dict, ...]:
    """Un registro por estudiante con reserva de IP ese día; el código del estudiante se cambia por un seudónimo."""
    if fecha == FECHA_DEMO:
        return tuple(DEMO)
    with SILVER_RESERVAS.open(encoding='utf-8') as entrada:
        del_dia = [r for r in csv.DictReader(entrada)
                   if r['fecha_inicio'][:10] == fecha and r['codigo_servicio'] == SERVICIO_IP and r['estado_reserva'] in ESTADOS_ATENDIDOS]
    proposito = {e['id_reserva']: e[PROPOSITO] for e in _leer_plata('encuesta_previa_normal_ip')}
    anteriores = defaultdict(list)
    for nombre in ('encuesta_satisfaccion_normal', 'encuesta_satisfaccion_express'):
        for e in _leer_plata(nombre):
            if e['fecha_inicio'][:10] < fecha:
                anteriores[e['codigo_usuario']].append(e)
    estudiantes, vistos = [], set()
    for reserva in sorted(del_dia, key=lambda r: r['fecha_inicio']):
        if reserva['codigo_usuario'] in vistos:
            continue
        vistos.add(reserva['codigo_usuario'])
        recientes = sorted(anteriores[reserva['codigo_usuario']], key=lambda e: e['fecha_inicio'])[-ENCUESTAS_ANTERIORES:]
        estudiantes.append({
            'estudiante': f'Estudiante {len(estudiantes) + 1}', 'hora': reserva['fecha_inicio'][11:16],
            'proposito': proposito.get(reserva['id_reserva'], 'sin encuesta previa'),
            'comprension': [e[COMPRENSION] for e in recientes if e.get(COMPRENSION, '').strip()],
            'comentarios': [e[c] for e in recientes for c in COMENTARIOS if e.get(c, '').strip()],
        })
    return tuple(estudiantes)


def reservas_del_dia(fecha: str) -> dict:
    """Lo que el agente puede ver de las reservas de un día: sin comentarios ni códigos."""
    return {'fecha': fecha, 'reservas': [
        {'estudiante': e['estudiante'], 'hora': e['hora'], 'proposito': e['proposito'],
         'comentarios_anteriores': len(e['comentarios'])}
        for e in estudiantes_del_dia(fecha)]}


def temas_mencionados(fecha: str, estudiante: str) -> dict:
    """Temas del curso que el estudiante mencionó en encuestas anteriores, extraídos por el modelo local."""
    registro = next((e for e in estudiantes_del_dia(fecha) if e['estudiante'].lower() == estudiante.lower()), None)
    if registro is None:
        return {'error': f'No hay una reserva de {estudiante} el {fecha}.'}
    comprension = [int(c) for c in registro['comprension'] if c.isdigit()]
    temas = []
    if registro['comentarios']:
        respuesta = generar(cliente_local(), INSTRUCCIONES_TEMAS, '\n'.join(f'- {c}' for c in registro['comentarios']),
                            modelo=MODELO_LOCAL, text=FORMATO_TEMAS)
        temas = json.loads(respuesta.texto)['temas']
    return {'estudiante': registro['estudiante'], 'temas_mencionados': temas,
            'comprension_promedio_1_a_5': round(statistics.mean(comprension), 1) if comprension else None,
            'comentarios_leidos': len(registro['comentarios'])}
