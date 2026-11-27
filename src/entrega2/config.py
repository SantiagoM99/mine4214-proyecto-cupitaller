"""Rutas y parámetros del proyecto. Los valores se pueden cambiar en `.env`."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Este archivo vive en src/entrega2/: la raíz del repositorio está dos niveles arriba.
RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / '.env')

DATA = RAIZ / 'data'
ARTIFACTS = RAIZ / 'artifacts' / 'entrega2'

# Bronce: documentos tal como llegan (no se versionan) y banco de preguntas escrito a mano.
DIR_VIGENTE = Path(os.getenv('E2_DIR_VIGENTE', DATA / 'bronce' / 'documentos' / 'vigentes')).expanduser()
DIR_HISTORICO = Path(os.getenv('E2_DIR_HISTORICO', DATA / 'bronce' / 'documentos' / 'historicos')).expanduser()
DIR_PREGUNTAS = DATA / 'bronce' / 'evaluacion'
PREGUNTAS = DIR_PREGUNTAS / 'preguntas.json'
# Plata: catálogo curado de documentos, páginas renderizadas y transcripciones por página.
CATALOGO = DATA / 'plata' / 'documentos' / 'catalogo_documentos.csv'
DIR_PAGINAS = DATA / 'plata' / 'documentos' / 'paginas'
DIR_TRANSCRIPCIONES = DATA / 'plata' / 'documentos' / 'transcripciones'
# Oro: Gold de la Entrega 1, oferta agregada y la copia de la bodega que consulta el agente.
GOLD_ENTREGA1 = DATA / 'oro' / 'bookeau.sqlite3'
SILVER_RESERVAS = DATA / 'plata' / 'reservas.csv'
OFERTA_POR_PERIODO = DATA / 'oro' / 'oferta_por_periodo.csv'
BODEGA = DATA / 'oro' / 'bookeau_agente.sqlite3'
# Salidas de las corridas (no se versionan).
DIR_RESULTADOS = ARTIFACTS / 'resultados'

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://mine4214:mine4214@127.0.0.1:5434/mine4214')
MODELO_EMBEDDINGS = os.getenv('EMBEDDING_MODEL', 'intfloat/multilingual-e5-small')
DIMENSIONES_EMBEDDING = 384
MODELO_LLM = os.getenv('OPENAI_MODEL', 'gpt-6-luna')
ARCHIVO_LLAVE = Path(os.getenv(
    'OPENAI_API_KEY_FILE', RAIZ / 'rag_lab_final' / 'rag_lab_final' / 'openai-key-2026-11-12.txt',
)).expanduser()

PERIODO_VIGENTE = '2026-20'

MODELO_JUEZ = os.getenv('OPENAI_JUDGE_MODEL', 'gpt-6-sol')

# Modelo de pesos abiertos para los experimentos que no pueden salir del equipo (Ollama).
URL_OLLAMA = os.getenv('OLLAMA_URL', 'http://localhost:11434/v1')
MODELO_LOCAL = os.getenv('MODELO_LOCAL', 'qwen3:30b-a3b-instruct-2507-q4_K_M')
MODELO_LOCAL_RAZONADOR = os.getenv('MODELO_LOCAL_RAZONADOR', 'qwen3:30b-a3b')

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
