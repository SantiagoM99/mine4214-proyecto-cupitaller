"""Experimento de índices: latencia y recall de la búsqueda vectorial con y sin índice.

Compara, sobre la misma tabla y las mismas consultas, la búsqueda exacta sin índice con
HNSW (vector y halfvec), IVFFlat y cuantización binaria con re-ranqueo. Se mide sobre los
753 fragmentos reales de la colección visual y sobre tablas sintéticas de 10 mil, 100 mil
y 1 millón de vectores, porque con el corpus real cualquier opción tarda milisegundos y
la tabla no mostraría desde qué tamaño el índice empieza a pagar.

Los vectores sintéticos son fragmentos reales más ruido gaussiano (coseno medio de 0,85
con su original), para conservar la estructura de grupos del corpus: vectores uniformes
en la esfera no tienen vecinos cercanos y castigan a los índices aproximados.

Las consultas son los embeddings de las 200 preguntas sintéticas. El recall@5 se mide
contra el resultado exacto de la misma tabla. Todo vive en el esquema `experimentos`.

    python3 src/entrega2/exp_indices.py [--tamanos 10000 100000 1000000]
"""

import argparse
import json
import math
import statistics
import time

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from base_vectorial import embedding_de_pregunta
from config import DATABASE_URL, DIR_RESULTADOS

DIR_EXPERIMENTOS = DIR_RESULTADOS / 'experimentos'
ARCHIVO = DIR_EXPERIMENTOS / 'indices.json'
K = 5
SEMILLA = 20261127
SIGMA_RUIDO = 0.0316  # 1 / sqrt(1 + 384 sigma^2) = 0.85
CANDIDATOS_BINARIO = 40


def conectar() -> psycopg.Connection:
    conexion = psycopg.connect(DATABASE_URL, autocommit=True)
    register_vector(conexion)
    conexion.execute('CREATE SCHEMA IF NOT EXISTS experimentos')
    conexion.execute("SET maintenance_work_mem = '4GB'")
    conexion.execute('SET max_parallel_maintenance_workers = 7')
    return conexion


def vectores_reales(conexion) -> np.ndarray:
    filas = conexion.execute("SELECT embedding FROM fragmentos WHERE coleccion = 'visual' ORDER BY id").fetchall()
    return np.array([f[0].to_numpy() for f in filas], dtype=np.float32)


def sinteticos(base: np.ndarray, n: int) -> np.ndarray:
    generador = np.random.default_rng(SEMILLA)
    extra = base[generador.integers(0, len(base), n - len(base))]
    extra = extra + generador.normal(0, SIGMA_RUIDO, extra.shape).astype(np.float32)
    extra /= np.linalg.norm(extra, axis=1, keepdims=True)
    return np.vstack([base, extra])


def cargar_tabla(conexion, tabla: str, vectores: np.ndarray) -> None:
    conexion.execute(f'DROP TABLE IF EXISTS {tabla}')
    conexion.execute(f'CREATE TABLE {tabla} (id int PRIMARY KEY, embedding vector(384))')
    with conexion.cursor() as cursor, cursor.copy(f'COPY {tabla} (id, embedding) FROM STDIN WITH (FORMAT BINARY)') as copia:
        copia.set_types(['int4', 'vector'])
        for i, v in enumerate(vectores):
            copia.write_row((i, v))
    conexion.execute(f'VACUUM ANALYZE {tabla}')


def _sql_busqueda(tabla: str, tipo: str) -> str:
    if tipo == 'halfvec':
        return f'SELECT id FROM {tabla} ORDER BY embedding::halfvec(384) <=> %(q)s::halfvec(384) LIMIT {K}'
    if tipo == 'binario':
        return (f'SELECT id FROM (SELECT id, embedding FROM {tabla} '
                f'ORDER BY binary_quantize(embedding)::bit(384) <~> binary_quantize(%(q)s::vector(384)) LIMIT {CANDIDATOS_BINARIO}) c '
                f'ORDER BY embedding <=> %(q)s::vector(384) LIMIT {K}')
    return f'SELECT id FROM {tabla} ORDER BY embedding <=> %(q)s::vector(384) LIMIT {K}'


def medir(conexion, tabla: str, tipo: str, consultas: np.ndarray, ajustes: dict[str, str]) -> tuple[dict, list[set]]:
    sql = _sql_busqueda(tabla, tipo)
    for nombre, valor in ajustes.items():
        conexion.execute(f'SET {nombre} = {valor}')
    with conexion.cursor() as cursor:
        cursor.execute(f'EXPLAIN {sql}', {'q': consultas[0]})
        plan = ' '.join(f[0] for f in cursor.fetchall())
        for q in consultas[:20]:  # calentamiento: lleva la tabla y el índice a memoria
            cursor.execute(sql, {'q': q}, prepare=True)
            cursor.fetchall()
        tiempos, resultados = [], []
        for q in consultas:
            inicio = time.perf_counter()
            cursor.execute(sql, {'q': q}, prepare=True)
            ids = {f[0] for f in cursor.fetchall()}
            tiempos.append((time.perf_counter() - inicio) * 1000)
            resultados.append(ids)
    for nombre in ajustes:
        conexion.execute(f'RESET {nombre}')
    tiempos.sort()
    usa_indice = 'Index Scan' in plan
    return {
        'latencia_p50_ms': round(statistics.median(tiempos), 3),
        'latencia_p95_ms': round(tiempos[int(0.95 * len(tiempos)) - 1], 3),
        'usa_indice': usa_indice,
    }, resultados


def crear_indice(conexion, tabla: str, ddl: str) -> dict:
    inicio = time.perf_counter()
    conexion.execute(ddl.format(tabla=tabla, nombre=f'{tabla.split(".")[1]}_idx'))
    segundos = time.perf_counter() - inicio
    tamano = conexion.execute(f"SELECT pg_relation_size('{tabla}_idx')").fetchone()[0]
    return {'construccion_s': round(segundos, 2), 'tamano_mb': round(tamano / 2**20, 2)}


def configuraciones(n: int) -> list[dict]:
    listas = max(1, round(math.sqrt(n)))
    return [
        {'nombre': 'HNSW (m=16, ef_construction=64), ef_search=40', 'tipo': 'vector',
         'ddl': 'CREATE INDEX {nombre} ON {tabla} USING hnsw (embedding vector_cosine_ops)',
         'ajustes': {'hnsw.ef_search': '40', 'enable_seqscan': 'off'}},
        {'nombre': 'HNSW, ef_search=100', 'tipo': 'vector', 'mismo_indice': True,
         'ajustes': {'hnsw.ef_search': '100', 'enable_seqscan': 'off'}},
        {'nombre': f'IVFFlat (lists={listas}), probes=1', 'tipo': 'vector',
         'ddl': f'CREATE INDEX {{nombre}} ON {{tabla}} USING ivfflat (embedding vector_cosine_ops) WITH (lists = {listas})',
         'ajustes': {'ivfflat.probes': '1', 'enable_seqscan': 'off'}},
        {'nombre': f'IVFFlat (lists={listas}), probes={max(1, round(math.sqrt(listas)))}', 'tipo': 'vector', 'mismo_indice': True,
         'ajustes': {'ivfflat.probes': str(max(1, round(math.sqrt(listas)))), 'enable_seqscan': 'off'}},
        {'nombre': 'HNSW sobre halfvec (16 bits)', 'tipo': 'halfvec',
         'ddl': 'CREATE INDEX {nombre} ON {tabla} USING hnsw ((embedding::halfvec(384)) halfvec_cosine_ops)',
         'ajustes': {'hnsw.ef_search': '40', 'enable_seqscan': 'off'}},
        {'nombre': f'HNSW binario (1 bit) + re-ranqueo de {CANDIDATOS_BINARIO}', 'tipo': 'binario',
         'ddl': 'CREATE INDEX {nombre} ON {tabla} USING hnsw ((binary_quantize(embedding)::bit(384)) bit_hamming_ops)',
         'ajustes': {'hnsw.ef_search': str(CANDIDATOS_BINARIO), 'enable_seqscan': 'off'}},
    ]


def experimento(conexion, etiqueta: str, vectores: np.ndarray, consultas: np.ndarray) -> list[dict]:
    tabla = f'experimentos.v_{etiqueta}'
    inicio = time.perf_counter()
    cargar_tabla(conexion, tabla, vectores)
    print(f'{etiqueta}: {len(vectores)} vectores cargados en {time.perf_counter() - inicio:.1f} s', flush=True)
    tamano_tabla = conexion.execute(f"SELECT pg_total_relation_size('{tabla}')").fetchone()[0]
    exacto, verdad = medir(conexion, tabla, 'vector', consultas, {})
    filas = [{'vectores': len(vectores), 'configuracion': 'Sin índice (búsqueda exacta)', **exacto,
              'recall_k5': 1.0, 'construccion_s': 0, 'tamano_mb': 0, 'tabla_mb': round(tamano_tabla / 2**20, 1)}]
    print(f"  {filas[-1]['configuracion']:<50} p50 {exacto['latencia_p50_ms']:>8} ms", flush=True)
    construccion = {}
    for config in configuraciones(len(vectores)):
        if not config.get('mismo_indice'):
            conexion.execute(f'DROP INDEX IF EXISTS {tabla}_idx')
            construccion = crear_indice(conexion, tabla, config['ddl'])
        metricas, resultados = medir(conexion, tabla, config['tipo'], consultas, config['ajustes'])
        recall = statistics.mean(len(a & b) / K for a, b in zip(resultados, verdad, strict=True))
        filas.append({'vectores': len(vectores), 'configuracion': config['nombre'], **metricas,
                      'recall_k5': round(recall, 3), **construccion, 'tabla_mb': round(tamano_tabla / 2**20, 1)})
        print(f"  {config['nombre']:<50} p50 {metricas['latencia_p50_ms']:>8} ms  recall {recall:.3f}  "
              f"índice {construccion['tamano_mb']} MB en {construccion['construccion_s']} s  usa índice: {metricas['usa_indice']}", flush=True)
    conexion.execute(f'DROP TABLE {tabla}')
    return filas


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumentos.add_argument('--tamanos', type=int, nargs='*', default=[10_000, 100_000, 1_000_000])
    tamanos = argumentos.parse_args().tamanos
    preguntas = json.loads((DIR_EXPERIMENTOS / 'preguntas_sinteticas.json').read_text(encoding='utf-8'))
    consultas = np.array([embedding_de_pregunta(p['pregunta']) for p in preguntas], dtype=np.float32)
    with conectar() as conexion:
        reales = vectores_reales(conexion)
        filas = experimento(conexion, 'real', reales, consultas)
        ARCHIVO.write_text(json.dumps(filas, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        for n in tamanos:
            filas += experimento(conexion, str(n), sinteticos(reales, n), consultas)
            ARCHIVO.write_text(json.dumps(filas, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
