"""Acceso a la base vectorial: esquema, carga de fragmentos y búsqueda por similitud."""

import hashlib
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from catalogo import Documento
from config import DATABASE_URL, MODELO_EMBEDDINGS, RAIZ

COLECCIONES = ('texto', 'visual')


@dataclass(frozen=True)
class Fragmento:
    clave: str
    titulo: str
    periodo: str
    vigente: bool
    nivel: int | None
    pagina: int
    contenido: str
    similitud: float

    @property
    def origen(self) -> str:
        return f'{self.clave} p. {self.pagina}'


def conectar() -> psycopg.Connection:
    conexion = psycopg.connect(DATABASE_URL)
    conexion.execute((RAIZ / 'sql' / 'base_vectorial.sql').read_text(encoding='utf-8'))
    conexion.commit()
    register_vector(conexion)
    return conexion


@lru_cache(maxsize=1)
def modelo_de_embeddings() -> SentenceTransformer:
    return SentenceTransformer(MODELO_EMBEDDINGS)


# Los modelos E5 se entrenaron con estos prefijos; sin ellos la similitud entre
# preguntas y pasajes se degrada.
def embeddings_de_pasajes(textos: list[str]) -> np.ndarray:
    return modelo_de_embeddings().encode(
        [f'passage: {texto}' for texto in textos], normalize_embeddings=True, show_progress_bar=False,
    )


def embedding_de_pregunta(pregunta: str) -> np.ndarray:
    return modelo_de_embeddings().encode(f'query: {pregunta}', normalize_embeddings=True)


def _registrar_documento(cursor: psycopg.Cursor, doc: Documento) -> int:
    cursor.execute(
        """
        INSERT INTO documentos (clave, titulo, tipo, periodo, vigente, nivel, archivo, sha256)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (clave) DO UPDATE SET
            titulo = EXCLUDED.titulo, tipo = EXCLUDED.tipo, periodo = EXCLUDED.periodo,
            vigente = EXCLUDED.vigente, nivel = EXCLUDED.nivel, archivo = EXCLUDED.archivo,
            sha256 = EXCLUDED.sha256, cargado_en = now()
        RETURNING id
        """,
        (doc.clave, doc.titulo, doc.tipo, doc.periodo, doc.vigente, doc.nivel, doc.archivo,
         hashlib.sha256(doc.ruta.read_bytes()).hexdigest()),
    )
    return cursor.fetchone()[0]


def reemplazar_fragmentos(
    conexion: psycopg.Connection, doc: Documento, coleccion: str, fragmentos: list[tuple[int, int, str]],
) -> int:
    """Carga los fragmentos (página, índice, contenido) de un documento en una colección."""
    vectores = embeddings_de_pasajes([f'{doc.titulo}\n{contenido}' for _, _, contenido in fragmentos]) if fragmentos else []
    with conexion.transaction(), conexion.cursor() as cursor:
        documento_id = _registrar_documento(cursor, doc)
        cursor.execute('DELETE FROM fragmentos WHERE documento_id = %s AND coleccion = %s', (documento_id, coleccion))
        cursor.executemany(
            """
            INSERT INTO fragmentos (documento_id, coleccion, pagina, indice, contenido, palabras, modelo_embedding, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (documento_id, coleccion, pagina, indice, contenido, len(contenido.split()), MODELO_EMBEDDINGS, vector)
                for (pagina, indice, contenido), vector in zip(fragmentos, vectores, strict=True)
            ],
        )
    return len(fragmentos)


def buscar(
    conexion: psycopg.Connection, pregunta: str, *, coleccion: str, k: int = 5, solo_vigentes: bool = False,
    semestre: str | None = None,
) -> list[Fragmento]:
    """Los k fragmentos más parecidos a la pregunta dentro de una colección, opcionalmente de un solo semestre."""
    vector = embedding_de_pregunta(pregunta)
    with conexion.transaction(), conexion.cursor() as cursor:
        # Con filtros (colección, vigencia) el índice HNSW puede devolver menos de k filas
        # porque filtra después de recorrer el grafo; el recorrido iterativo sigue buscando
        # hasta completar k sin perder el orden por distancia.
        cursor.execute("SET LOCAL hnsw.iterative_scan = 'strict_order'")
        cursor.execute(
            """
            SELECT d.clave, d.titulo, d.periodo, d.vigente, d.nivel, f.pagina, f.contenido,
                   1 - (f.embedding <=> %(vector)s) AS similitud
            FROM fragmentos f
            JOIN documentos d ON d.id = f.documento_id
            WHERE f.coleccion = %(coleccion)s AND (d.vigente OR NOT %(solo_vigentes)s)
              AND (%(semestre)s::text IS NULL OR d.periodo = %(semestre)s)
            ORDER BY f.embedding <=> %(vector)s
            LIMIT %(k)s
            """,
            {'vector': vector, 'coleccion': coleccion, 'solo_vigentes': solo_vigentes, 'semestre': semestre, 'k': k},
        )
        return [Fragmento(*fila) for fila in cursor.fetchall()]


def resumen(conexion: psycopg.Connection) -> list[tuple]:
    """Documentos, fragmentos y palabras por colección y vigencia."""
    return conexion.execute(
        """
        SELECT f.coleccion, d.vigente, count(DISTINCT d.id), count(*), sum(f.palabras)
        FROM fragmentos f JOIN documentos d ON d.id = f.documento_id
        GROUP BY f.coleccion, d.vigente ORDER BY f.coleccion, d.vigente DESC
        """
    ).fetchall()
