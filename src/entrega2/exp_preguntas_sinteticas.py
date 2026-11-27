"""Banco sintético de preguntas para medir la recuperación de los experimentos de chunking.

El banco escrito a mano tiene 22 preguntas con fuente: una pregunta equivale a 4,5 puntos
de recuperación@5, y las variantes de chunking difieren en menos que eso. Este banco
genera una pregunta por página en una muestra de páginas vigentes; la fuente esperada
es la página de la que salió la pregunta. Solo sirve para medir recuperación, no la
calidad de la respuesta: la respuesta la escribe el mismo modelo que la pregunta.

    python3 src/entrega2/exp_preguntas_sinteticas.py
"""

import json
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from catalogo import cargar_catalogo
from config import DIR_RESULTADOS
from llm import cliente, generar
from transcribir import leer_transcripcion, paginas_del_documento

DIR_EXPERIMENTOS = DIR_RESULTADOS / 'experimentos'
ARCHIVO = DIR_EXPERIMENTOS / 'preguntas_sinteticas.json'
PAGINAS_EN_LA_MUESTRA = 200
MIN_PALABRAS = 25
SEMILLA = 20261127

INSTRUCCIONES = """Recibes una página de material del curso Introducción a la Programación.
Escribe una pregunta que un estudiante del curso haría y que se responda con esa página.

- Redacta la pregunta con tus palabras: no copies frases de la página ni nombres de variables salvo que sean el tema.
- No menciones "la diapositiva", "la página" ni "el documento".
- La respuesta debe estar en la página; escríbela en una frase."""

FORMATO = {'format': {
    'type': 'json_schema', 'name': 'pregunta', 'strict': True,
    'schema': {
        'type': 'object',
        'properties': {'pregunta': {'type': 'string'}, 'respuesta': {'type': 'string'}},
        'required': ['pregunta', 'respuesta'], 'additionalProperties': False,
    },
}}


def muestra_de_paginas() -> list:
    """Páginas vigentes con texto suficiente, repartidas en proporción al tamaño de cada documento."""
    por_documento = defaultdict(list)
    for doc in cargar_catalogo():
        if doc.vigente:
            for pagina in paginas_del_documento(doc):
                if len(leer_transcripcion(pagina).split()) >= MIN_PALABRAS:
                    por_documento[doc.clave].append(pagina)
    candidatas = [pagina for paginas in por_documento.values() for pagina in paginas]
    return random.Random(SEMILLA).sample(candidatas, min(PAGINAS_EN_LA_MUESTRA, len(candidatas)))


def main() -> None:
    api = cliente()
    paginas = muestra_de_paginas()

    def preguntar(pagina) -> dict:
        texto = f'Documento: {pagina.documento.titulo}\n\n{leer_transcripcion(pagina)}'
        generada = json.loads(generar(api, INSTRUCCIONES, texto, text=FORMATO).texto)
        return {
            'id': f'sint-{pagina.documento.clave}-p{pagina.numero}',
            'pregunta': generada['pregunta'], 'respuesta_esperada': generada['respuesta'],
            'fuentes': [{'clave': pagina.documento.clave, 'paginas': [pagina.numero]}],
        }

    with ThreadPoolExecutor(8) as hilos:
        banco = list(hilos.map(preguntar, paginas))
    ARCHIVO.write_text(json.dumps(banco, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(banco)} preguntas en {ARCHIVO}')


if __name__ == '__main__':
    main()
