"""Juez automático: califica cada respuesta contra la respuesta esperada de la pregunta.

Usa un modelo distinto del que genera las respuestas (MODELO_JUEZ), para que el
generador no califique su propio trabajo. Los veredictos se guardan aparte de las
respuestas y se pueden revisar o corregir a mano.
"""

import json

from openai import OpenAI

from config import MODELO_JUEZ
from llm import generar

VEREDICTOS = ('correcta', 'parcial', 'incorrecta')

INSTRUCCIONES = """Calificas la respuesta de un asistente a una pregunta sobre un curso universitario, comparándola con la respuesta esperada.

Veredicto:
- correcta: contiene todos los hechos de la respuesta esperada y no los contradice. El formato, el orden y los detalles adicionales que sean ciertos no importan.
- parcial: contiene parte de los hechos esperados, o los contiene junto con un dato equivocado.
- incorrecta: no contiene los hechos esperados, o dice que no hay información cuando sí se esperaba una respuesta.

Si la pregunta no es respondible con los documentos, la respuesta es correcta solo si el asistente dice que no hay información suficiente, e incorrecta si responde con un dato.

alucinacion es true cuando la respuesta afirma un hecho concreto que contradice la respuesta esperada o que el asistente no podía saber (por ejemplo, responder con un dato a una pregunta no respondible). Abstenerse no es alucinar."""

FORMATO = {'format': {
    'type': 'json_schema',
    'name': 'veredicto',
    'strict': True,
    'schema': {
        'type': 'object',
        'properties': {
            'veredicto': {'type': 'string', 'enum': list(VEREDICTOS)},
            'alucinacion': {'type': 'boolean'},
            'motivo': {'type': 'string', 'description': 'Una frase.'},
        },
        'required': ['veredicto', 'alucinacion', 'motivo'],
        'additionalProperties': False,
    },
}}


def juzgar(api: OpenAI, pregunta: dict, respuesta: str) -> dict:
    """Veredicto para una respuesta. `pregunta` es una entrada de data/bronce/evaluacion/preguntas.json."""
    caso = json.dumps({
        'pregunta': pregunta['pregunta'],
        'respondible_con_los_documentos': pregunta['respondible'],
        'respuesta_esperada': pregunta['respuesta_esperada'],
        'respuesta_del_asistente': respuesta,
    }, ensure_ascii=False, indent=2)
    return json.loads(generar(api, INSTRUCCIONES, caso, modelo=MODELO_JUEZ, text=FORMATO).texto)
