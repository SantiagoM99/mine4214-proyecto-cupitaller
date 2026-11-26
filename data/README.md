# Datos

`data/` sigue la arquitectura medallón (Bronze → Silver → Gold) y la comparten las dos entregas. Los datos reales no se versionan: los de la Entrega 1 contienen datos personales (nombres, correos y códigos de estudiantes y monitores, y comentarios abiertos) y los documentos de la Entrega 2 son material del curso con derechos reservados.

Para reproducir la Entrega 1:

1. Copiar `Bookeau.zip` (compartido por la coordinación de CupiTaller) en `data/bronce/` y descomprimirlo como `data/bronce/Bookeau/`. Incluye las carpetas de reservas y encuestas y `horarios/` (oferta por semestre, sin datos personales).
2. Desde la raíz del proyecto, ejecutar `python3 src/main.py`, que corre todos los pasos en orden. Se regeneran `data/plata/` (Silver) y `data/oro/` (Gold, incluida `bookeau.sqlite3`).

## Datos ficticios para probar el flujo

`python3 src/main.py --dummy` genera libros de Excel inventados (sin información personal) en `data/bronce/dummy/` y ejecuta todo el pipeline sobre ellos. Los libros se guardan en `data/bronce/dummy/` (no toca `data/bronce/Bookeau/`) y el resto del flujo es el mismo: Silver en `data/plata/`, Gold en `data/oro/` y evidencia y tablero en `artifacts/entrega1/`. Por eso **reemplaza los resultados que hubiera**; para volver a los reales basta ejecutar `python3 src/main.py` sin `--dummy`. Los libros ficticios sí se pueden versionar.

## Documentos de la Entrega 2

Copiar los PDF y la presentación del curso en `data/bronce/documentos/vigentes/` (2026-20: programa y 44 presentaciones, en las subcarpetas que indica el catálogo) y `data/bronce/documentos/historicos/` (2020-20 y 2021-10). Las rutas exactas están en la columna `archivo` de `data/plata/documentos/catalogo_documentos.csv`. Luego, `python3 src/main.py --entrega 2` (ver el README principal).

## Capas

| Capa | Carpeta | Entrega 1 | Entrega 2 |
|---|---|---|---|
| Bronze | `data/bronce/` | `Bookeau/` (ZIP, 114 Excel de reservas y encuestas y 30 de horarios, sin modificar) y `dummy/` | `documentos/vigentes/`, `documentos/historicos/` (PDF sin modificar) y `evaluacion/` (banco de preguntas) |
| Silver | `data/plata/` | 6 CSV limpios (reservas, cuatro encuestas y horarios) con trazabilidad y banderas | `documentos/`: catálogo curado, páginas renderizadas y transcripciones por página |
| Gold | `data/oro/` | Dimensiones, hechos y base SQLite `bookeau.sqlite3` | `oferta_por_periodo.csv` y `bookeau_agente.sqlite3` (copia del Gold con las vistas del agente) |

Se versionan solo `bronce/dummy/`, `bronce/evaluacion/`, `plata/documentos/catalogo_documentos.csv` y `oro/oferta_por_periodo.csv`.
