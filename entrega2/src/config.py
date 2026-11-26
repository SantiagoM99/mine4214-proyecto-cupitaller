"""Rutas y parámetros del proyecto. Los valores se pueden cambiar en `.env`."""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / '.env')

DIR_VIGENTE = RAIZ / 'documentos_rag'
DIR_HISTORICO = RAIZ / 'data antigua'
CATALOGO = RAIZ / 'data' / 'catalogo_documentos.csv'
DIR_PAGINAS = RAIZ / 'data' / 'paginas'
DIR_TRANSCRIPCIONES = RAIZ / 'data' / 'transcripciones'
BODEGA = RAIZ / 'data' / 'bodega' / 'bookeau.sqlite3'
OFERTA_POR_PERIODO = RAIZ / 'data' / 'oferta_por_periodo_entrega1.csv'
PREGUNTAS = RAIZ / 'data' / 'evaluacion' / 'preguntas.json'
DIR_RESULTADOS = RAIZ / 'resultados'

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://mine4214:mine4214@127.0.0.1:5434/mine4214')
MODELO_EMBEDDINGS = os.getenv('EMBEDDING_MODEL', 'intfloat/multilingual-e5-small')
DIMENSIONES_EMBEDDING = 384
MODELO_LLM = os.getenv('OPENAI_MODEL', 'gpt-6-luna')
ARCHIVO_LLAVE = Path(os.getenv(
    'OPENAI_API_KEY_FILE', RAIZ / 'rag_lab_final' / 'rag_lab_final' / 'openai-key-2026-11-12.txt',
)).expanduser()

PERIODO_VIGENTE = '2026-20'

MODELO_JUEZ = os.getenv('OPENAI_JUDGE_MODEL', 'gpt-6-sol')

# Precio de lista de gpt-6-luna en USD por millón de tokens, consultado el 2026-11-24 en
# rastreadores de precios que citan la página oficial de OpenAI. La lectura de caché cuesta
# 0,1 veces la entrada y la escritura (retención de 30 minutos) 1,25 veces, según la guía
# de prompt caching. Verificar antes de reutilizar las cifras de costo:
# https://developers.openai.com/api/docs/pricing
PRECIO_USD_POR_MILLON = {'entrada': 0.10, 'lectura_de_cache': 0.01, 'escritura_en_cache': 0.125, 'salida': 0.50}


def costo_usd(uso: dict) -> float:
    """Costo de una llamada a partir de su registro de tokens."""
    leidos = uso['tokens_en_cache']
    escritos = uso.get('tokens_escritos_en_cache', 0)
    return (
        (uso['tokens_entrada'] - leidos - escritos) * PRECIO_USD_POR_MILLON['entrada']
        + leidos * PRECIO_USD_POR_MILLON['lectura_de_cache']
        + escritos * PRECIO_USD_POR_MILLON['escritura_en_cache']
        + uso['tokens_salida'] * PRECIO_USD_POR_MILLON['salida']
    ) / 1_000_000
