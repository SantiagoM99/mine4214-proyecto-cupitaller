# Proyecto MINE-4214 · Entrega 2 · Documentos y bodega de CupiTaller

Segunda entrega del proyecto de Modelado y Diseño de Datos (Uniandes, 2026-2). Integra los documentos del curso Introducción a la Programación (programas y presentaciones de clase, en PDF) con la bodega de reservas y encuestas de CupiTaller construida en la Entrega 1.

El proyecto compara dos formas de responder con los documentos, **prompting directo** y **RAG**, muestra cómo falla un RAG cuando el corpus mezcla versiones de un mismo documento, e implementa un **agente** que contrasta lo que dicen los documentos con lo que registra la bodega.

## Entregables

| Producto | Archivo |
|---|---|
| Informe (LaTeX y PDF) | [`docs/informe/informe.pdf`](docs/informe/informe.pdf) |
| Póster de 70 × 100 cm | [`docs/poster/poster.pdf`](docs/poster/poster.pdf). Fuente en `poster.html`; `docs/poster/exportar.sh` genera el PDF y `medir.sh` dice cuántos milímetros sobran o faltan en cada columna |
| Código fuente | `src/`, `sql/`, `scripts/` |
| Resultados de las corridas | `resultados/` |

## Qué hace cada parte

| Paso | Script | Qué hace |
|---|---|---|
| `catalogo` | `src/catalogo.py` | Propone `data/catalogo_documentos.csv`: una fila por documento con semestre, vigencia y nivel. Se corrige a mano y es la fuente de las etiquetas |
| `transcribir` | `src/transcribir.py` | Ingesta visual: renderiza cada página y un modelo con visión la transcribe (texto, código de las capturas, tablas y figuras) |
| `indexar` | `src/indexar.py` | Chunking por página, embeddings (`multilingual-e5-small`) y carga en pgvector. Dos colecciones: `texto` (capa de texto del PDF) y `visual` (transcripciones) |
| `bodega` | `src/bodega.py` | Copia el Gold de la Entrega 1, retira los comentarios de texto libre, añade `agg_tipos_de_horario` y `agg_oferta_periodo` (capacidad y ocupación por semestre, de `data/oferta_por_periodo_entrega1.csv`), comprueba que la oferta por franja de `hecho_oferta` cuadre con ella y crea las vistas que consulta el agente, entre ellas `v_oferta_franja`. Si el Gold se construyó sin los archivos de horarios, el agente usa `agg_demanda_franja`, los mismos conteos reconstruidos desde las reservas (regla R05), sin capacidad por franja |
| `evaluar` | `src/evaluar.py` | Responde 26 preguntas con prompting directo, RAG de texto y RAG visual, y las califica con un modelo juez |
| `entropia` | `src/poc_entropia.py` | Prueba de concepto con las dos versiones del programa del curso (2020-20 y 2026-20) |
| `agente` | `src/casos_agente.py` | Casos del agente híbrido; `src/agente.py "pregunta"` lo consulta desde la terminal |
| `figuras` | `src/figuras.py` | Gráficas del informe |
| `temas` | `src/temas_por_nivel.py` | Qué clases de 2026-20 tienen versión en el material de 2020-21; tabla del informe |
| `poster` | `src/figuras_poster.py` | Gráficas y recortes de documentos del póster, al tamaño de impresión |
| `modelo` | `src/modelo_dimensional.py` | Diagrama del modelo dimensional para el póster; se detiene si no coincide con el DDL de `sql/bodega_modelo_gold.sql` |

Los enfoques están en `src/enfoques.py`, el acceso a la base vectorial en `src/base_vectorial.py`, el juez en `src/juez.py` y las llamadas al modelo, con su registro de tokens y tiempo, en `src/llm.py`.

## Ejecutar

Requisitos: Python 3.12, Postgres 18 con pgvector, LibreOffice (convierte la presentación `.pptx`) y una llave de OpenAI.

```bash
brew install postgresql@18 pgvector          # una sola vez
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                         # ajustar OPENAI_API_KEY_FILE

scripts/postgres.sh iniciar                  # Postgres local en 127.0.0.1:5434
python3 src/main.py                          # todos los pasos
python3 src/main.py --lista                  # lista los pasos
python3 src/main.py --desde indexar          # retoma desde un paso
```

Los pasos que llaman al modelo guardan lo que producen (`data/transcripciones/`, `resultados/`) y no repiten lo ya hecho. Para volver a responder y calificar: `python3 src/evaluar.py --rehacer`.

Consultar el agente:

```bash
python3 src/agente.py "El programa menciona tutorías grupales. ¿Se siguen ofreciendo?"
```

## Datos

Ninguno de estos datos se versiona; `.gitignore` los excluye.

| Dato | Dónde | Por qué no se versiona |
|---|---|---|
| Documentos vigentes (2026-20): programa y 44 presentaciones | `documentos_rag/` | Material del curso con derechos reservados de la Universidad |
| Documentos históricos (2020-20 y 2021-10): programa y 12 presentaciones | `data antigua/` | Igual |
| Bodega Gold de la Entrega 1 | `data/bodega/bookeau.sqlite3` | Datos de estudiantes |
| Páginas renderizadas y transcripciones | `data/paginas/`, `data/transcripciones/` | Se derivan de los documentos |

`python3 src/bodega.py` toma por defecto el Gold y el Silver de la Entrega 1 en `../data/` (la raíz de este repositorio). El Gold debe ser el de la versión final de esa entrega (reglas R01 a R07, 83.894 reservas); si es anterior, el paso se detiene y lo dice. Otras rutas: `--gold` y `--silver-reservas`.

## Decisiones de diseño

- **La página es la unidad de chunking.** Una diapositiva es una idea. Solo se parten las páginas de más de 200 palabras (las del programa), entre líneas para no romper código ni tablas.
- **La visión se usa al ingerir, no al buscar.** Las presentaciones llevan el código como capturas de pantalla y el programa 2020-20 es un escaneo sin capa de texto. Transcribir cada página una vez permite seguir usando embeddings de texto y el esquema de pgvector del laboratorio del curso.
- **Semestre, vigencia y nivel son columnas del documento.** Son los filtros que controlan qué versión puede recuperar el RAG, así que viven en `documentos` y no en un JSONB.
- **El agente consulta vistas, no las tablas del modelo dimensional.** Las vistas resuelven los joins y nombran las columnas de forma que el modelo escriba SQL correcto. La conexión es de solo lectura, admite una sola sentencia `SELECT` y corta las consultas largas.
- **Lo que sale hacia el modelo externo no lleva datos personales.** La copia de la bodega no tiene los comentarios abiertos de las encuestas, `dim_programa` está vedada y las portadas de las presentaciones históricas (nombre y correo de quien dictó la sección) se omiten.
