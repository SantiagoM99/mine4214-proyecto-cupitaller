-- Base vectorial del corpus (Postgres + pgvector). Parte del esquema del laboratorio del
-- curso (documents / document_chunks) con dos cambios:
--   * el semestre, la vigencia y el nivel son columnas del documento, no claves de un JSONB,
--     porque son los filtros con los que se controla qué versión puede recuperar el RAG;
--   * cada fragmento pertenece a una colección, para comparar la ingesta de solo texto
--     ('texto') con la ingesta visual ('visual') sobre los mismos documentos.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documentos (
    id            BIGSERIAL PRIMARY KEY,
    clave         TEXT NOT NULL UNIQUE,
    titulo        TEXT NOT NULL,
    tipo          TEXT NOT NULL CHECK (tipo IN ('programa', 'presentacion')),
    periodo       TEXT NOT NULL,
    vigente       BOOLEAN NOT NULL,
    nivel         SMALLINT CHECK (nivel BETWEEN 1 AND 4),
    archivo       TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    cargado_en    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fragmentos (
    id               BIGSERIAL PRIMARY KEY,
    documento_id     BIGINT NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
    coleccion        TEXT NOT NULL CHECK (coleccion IN ('texto', 'visual')),
    pagina           INTEGER NOT NULL CHECK (pagina > 0),
    indice           INTEGER NOT NULL CHECK (indice >= 0),
    contenido        TEXT NOT NULL,
    palabras         INTEGER NOT NULL CHECK (palabras > 0),
    modelo_embedding TEXT NOT NULL,
    embedding        VECTOR(384) NOT NULL,
    UNIQUE (documento_id, coleccion, pagina, indice)
);

CREATE INDEX IF NOT EXISTS fragmentos_documento_idx ON fragmentos (documento_id);
CREATE INDEX IF NOT EXISTS fragmentos_coleccion_idx ON fragmentos (coleccion);
CREATE INDEX IF NOT EXISTS fragmentos_embedding_hnsw_idx
    ON fragmentos USING hnsw (embedding vector_cosine_ops);
