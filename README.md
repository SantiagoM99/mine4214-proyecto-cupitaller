# Proyecto MINE-4214 · Reservas y satisfacción en CupiTaller

Proyecto del curso Modelado y Diseño de Datos (Uniandes, 2026-2) sobre las reservas de tutoría y las encuestas de estudiantes de CupiTaller, exportadas de Bookeau (2016–2026). Parte de los datos en Excel y construye un lakehouse por capas (Bronze, Silver y Gold), un modelo dimensional y un tablero que responde dos análisis (Entrega 1). La Entrega 2 integra los documentos del curso Introducción a la Programación con esa bodega: compara prompting directo y RAG visual, mide la entropía documental e implementa un agente híbrido (RAG y SQL).

Todo vive en una sola estructura: `data/`, `docs/`, `src/`, `sql/`, `notebooks/` y `artifacts/`. Lo que pertenece a cada entrega se distingue por carpeta (`src/entrega1/`, `src/entrega2/`, `artifacts/entrega1/`, `artifacts/entrega2/`) o por prefijo (`e1_`, `e2_`) donde no hay subcarpetas. Ver [Estructura](#estructura).

## Entrega 1

| Producto | Archivo |
|---|---|
| **Informe** (LaTeX y PDF) | [`docs/entregables/e1_informe/informe_latex.pdf`](docs/entregables/e1_informe/informe_latex.pdf) |
| **Anexos** del informe (glosario, datos de apoyo, extensión de texto) | [`docs/entregables/e1_informe/anexos_latex.pdf`](docs/entregables/e1_informe/anexos_latex.pdf) |
| Tablero interactivo (abrir en el navegador, sin servidor) | [`docs/entregables/e1_tablero/tablero_bookeau.html`](docs/entregables/e1_tablero/tablero_bookeau.html) |

## Entrega 2

Requerimientos que cruzan los documentos del curso con la bodega de la Entrega 1: prompting directo frente a RAG visual, entropía documental y un agente híbrido (RAG y SQL). Toma el Gold y el Silver de la Entrega 1 de `data/oro/` y `data/plata/`. Cómo ejecutarla: [Entrega 2: ejecutar](#entrega-2-ejecutar).

| Producto | Archivo |
|---|---|
| **Informe** (LaTeX y PDF) | [`docs/entregables/e2_informe/informe.pdf`](docs/entregables/e2_informe/informe.pdf) |
| **Póster** de 70 × 100 cm | [`docs/entregables/e2_poster/poster.pdf`](docs/entregables/e2_poster/poster.pdf). Fuente en `poster.html`; `src/auxiliar/e2_exportar_poster.sh` genera el PDF y `src/auxiliar/e2_medir_poster.sh` dice cuántos milímetros sobran o faltan en cada columna |

Los PDF, el póster y el tablero están versionados: se pueden abrir sin ejecutar nada. Para recompilar el informe o volver a exportar el póster hay que generar antes sus figuras y tabla (pasos `figuras`, `temas`, `poster` y `modelo`), que quedan en `artifacts/entrega2/` y no se versionan. Ver [Recompilar informes y póster](#recompilar-informes-y-póster).

## Qué necesitas según lo que quieras hacer

| Quiero… | Necesito |
|---|---|
| Leer los informes, el póster y el tablero | Un visor de PDF y un navegador. Están en `docs/entregables/` |
| **Ejecutar la Entrega 1 con datos ficticios** | Python 3.10 o superior. Nada más: usa solo la biblioteca estándar |
| Abrir los cuadernos de `notebooks/` | Lo anterior y `jupyter` ([Cuadernos](#cuadernos)) |
| Ejecutar la Entrega 1 con los datos reales | `Bookeau.zip`, que entrega la coordinación de CupiTaller (no se distribuye) |
| Regenerar la tabla y el diagrama del modelo de la Entrega 2 (pasos `temas` y `modelo`) | Python 3.12, `pip install -r requirements.txt` y haber corrido la Entrega 1 (con datos ficticios basta). No necesita documentos, llave ni Postgres |
| Ejecutar la Entrega 2 completa | Todo lo de [Entrega 2: ejecutar](#entrega-2-ejecutar): los documentos del curso, los datos reales de la Entrega 1, Postgres con pgvector, LibreOffice y una llave de OpenAI |
| Recompilar los informes o exportar el póster | [Recompilar informes y póster](#recompilar-informes-y-póster) |

Los scripts `.sh` (`scripts/` y `src/auxiliar/`) son para bash (macOS o Linux; en Windows, WSL). Las instrucciones de macOS usan Homebrew; lo probado de punta a punta es la Entrega 1 con datos ficticios y los pasos `temas` y `modelo` de la Entrega 2 en Linux.

## Entrega 1: análisis

1. **Inasistencia, presión de cola y oferta** (coordinación de CupiTaller): tasa de inasistencia = No asistió / (Atendida + No asistió); proporción de solicitudes en cola (En cola / eventos); y, con los horarios, ocupación de la oferta, lista de espera y conversión de la cola a reserva. Por modalidad, día, hora y período.
2. **Satisfacción** (coordinación académica): proporción de calificaciones 1–3 por modalidad, servicio y período, con la media y la distribución como apoyo.

## Reglas de negocio

| Regla | Qué establece |
|---|---|
| **R01** | Las reservas «Finalizada» y «Realizada» se tratan como un solo estado de análisis, *Atendida*; el estado original se conserva. |
| **R02** | Las encuestas marcadas «Inválida» se excluyen de los análisis; quedan en Silver para auditoría. |
| **R03** | Para los análisis de Gold solo se incluyen reservas de tutorías (tipo de horario Normal, Express o Normal pico), y las encuestas de esas reservas. |
| **R04** | La cola no ocupa cupo: la inasistencia se mide solo sobre citas que llegaron a su hora (confirmada por la coordinación). «Cola cancelada por reservación» son solicitudes que terminaron en una reserva y se reportan aparte de «En cola». |
| **R05** | El reporte de horarios (oferta) cubre solo la categoría «Tutor Presencial»; con ella coincide exactamente con Reservas. La oferta se compara con esas reservas. |
| **R06** | En Gold, todos los estados de cancelación (a tiempo, con excusa, por sanción, sancionada y cancelación simple) se agrupan en un solo estado de análisis, «Cancelada»; el estado original se conserva. |
| **R07** | Las reservas abiertas se cierran: «En ejecución» es atendida; «Reservada» es atendida si tiene hora de llegada y prestador, y no asistió en los demás casos. |

## Entrega 1: ejecutar

Los datos reales no se distribuyen (contienen datos personales). El repositorio incluye **datos ficticios** con la misma estructura en `data/bronce/dummy/`, con los que se puede ejecutar todo el flujo.

**Requisito:** Python 3.10 o superior (`python3 --version`). El pipeline usa solo la biblioteca estándar: no hay que crear un entorno virtual ni instalar paquetes. `src/main.py` es el punto de entrada de las dos entregas: sin `--entrega`, ejecuta la Entrega 1 (`src/entrega1/main.py`).

### Inicio rápido con datos ficticios

Desde la raíz del repositorio:

```bash
python3 src/main.py --dummy
```

Tarda unos segundos y ejecuta los 8 pasos de Bronze a Gold. Al terminar:

| Resultado | Dónde |
|---|---|
| Silver (6 CSV) | `data/plata/` |
| Gold: base SQLite con el modelo dimensional | `data/oro/bookeau.sqlite3` (más un CSV por tabla) |
| Controles de conciliación e integridad | `artifacts/entrega1/transformacion/controles_gold.json` |
| Evidencia de caracterización, calidad y limpieza | `artifacts/entrega1/` |
| Tablero | `docs/entregables/e1_tablero/tablero_bookeau.html` (abrir en el navegador) |

Para consultar el modelo directamente: `sqlite3 data/oro/bookeau.sqlite3 < sql/e1_01_consultas_analisis.sql`.

Con datos ficticios los conteos son pequeños (≈1.700 reservas) y **no coinciden con las cifras del informe**, que se calcularon con los datos reales (83.894 reservas de tutoría). El tablero versionado en `docs/entregables/e1_tablero/` es el generado con los datos ficticios; las capturas del informe (`docs/entregables/e1_informe/img/tablero_*.png`) son del tablero con los datos reales.

### Opciones de `main.py`

```bash
python3 src/main.py --dummy                    # todo el flujo con datos ficticios
python3 src/main.py --dummy --regenerar-dummy  # vuelve a generar los Excel ficticios antes de ejecutar
python3 src/main.py                            # datos reales en data/bronce/Bookeau/ (ver data/README.md)
python3 src/main.py --lista                    # lista los pasos
python3 src/main.py --dummy --desde gold       # retoma desde un paso
python3 src/main.py --dummy --solo gold tablero
```

Cada ejecución sobrescribe `data/plata/`, `data/oro/`, `artifacts/entrega1/` y el tablero de `docs/entregables/e1_tablero/`.

`src/entrega1/main.py` ejecuta los pasos en este orden y se detiene si uno falla:

| Paso | Script | Qué hace |
|---|---|---|
| `caracterizar` | `src/entrega1/caracterizar_bookeau.py` | Perfilamiento de Bronze |
| `documentar` | `src/entrega1/documentar_caracterizacion.py` | Diccionario y documento de caracterización |
| `preparar` | `src/entrega1/preparar_analisis_bookeau.py` | Evidencia de calidad para los análisis |
| `limpiar` | `src/entrega1/limpiar_bookeau.py` | Bronze → Silver |
| `horarios` | `src/entrega1/procesar_horarios.py` | Horarios (oferta) Bronze → Silver, y conciliación con Reservas por franja |
| `comprobar` | `src/entrega1/comprobar_estados_encuestas.py` | Cruce de estados de reserva y encuestas |
| `gold` | `src/entrega1/construir_gold_bookeau.py` | Silver → Gold, con controles de integridad y conciliación |
| `tablero` | `src/entrega1/generar_tablero_bookeau.py` | Tablero HTML y resultados agregados |

### Cuadernos

Los cuadernos de `notebooks/` leen los resultados del pipeline, así que primero hay que ejecutar `python3 src/main.py --dummy`. Requieren Jupyter:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install jupyter ipykernel   # o pip install -r requirements.txt (incluye la Entrega 2)
jupyter lab notebooks/
```

Las salidas guardadas en los cuadernos corresponden a los datos ficticios.

### Datos reales

Quien tenga acceso a `Bookeau.zip` (compartido por la coordinación de CupiTaller) lo descomprime como `data/bronce/Bookeau/` y ejecuta `python3 src/main.py` (sin `--dummy`), que reemplaza el Silver y el Gold ficticios por los reales. Con datos reales los conteos coinciden con los del informe. Ver [`data/README.md`](data/README.md).

## Entrega 2: ejecutar

La Entrega 2 **no se puede reproducir completa solo con este repositorio**, porque depende de tres cosas que no se distribuyen:

1. **Los documentos del curso** (programa y presentaciones de Introducción a la Programación: 2026-20, 2020-20 y 2021-10, 58 archivos). Tienen derechos reservados de la Universidad. Hay que pedirlos al equipo y copiarlos en `data/bronce/documentos/vigentes/` y `data/bronce/documentos/historicos/` (las rutas exactas están en la columna `archivo` de `data/plata/documentos/catalogo_documentos.csv`; si los dejas en otra carpeta, indica `E2_DIR_VIGENTE` y `E2_DIR_HISTORICO` en `.env`).
2. **Los datos reales de la Entrega 1** (`Bookeau.zip`). El paso `bodega` valida que el Gold sea el de la versión final (reglas R01 a R07, 83.894 reservas) y se detiene si no lo es; con los datos ficticios no pasa esa validación.
3. **Una llave de la API de OpenAI.** Las llamadas al modelo tienen costo; los pasos guardan lo que producen y no repiten lo ya hecho.

### Instalar

Requisitos del sistema:

| Programa | Para qué | macOS (Homebrew) |
|---|---|---|
| Python 3.12 | Todo el código de la Entrega 2 | `brew install python@3.12` |
| PostgreSQL 18 con pgvector | Base vectorial (pasos `indexar`, `evaluar`, `entropia`, `agente`) | `brew install postgresql@18 pgvector` |
| LibreOffice | Convierte a PDF las presentaciones `.pptx` históricas; el comando `soffice` debe estar en el `PATH` | `brew install --cask libreoffice` |
| Conexión a internet | La primera vez, `sentence-transformers` descarga el modelo de embeddings `multilingual-e5-small` de Hugging Face, y se instala PyTorch (varios cientos de MB) | |

En Linux hay que instalar los equivalentes (Postgres 18 y pgvector desde el repositorio de PostgreSQL, `libreoffice-impress`; los nombres de paquete varían) y apuntar `scripts/e2_postgres.sh` a los binarios con `PG_BIN=/usr/lib/postgresql/18/bin`. Ese script crea el clúster con la configuración regional `en_US.UTF-8`, que tiene que existir en el sistema.

Entorno de Python y configuración, desde la raíz del repositorio:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # y ajustar OPENAI_API_KEY_FILE: ruta de un archivo de texto con la llave en una línea
```

### Ejecutar

```bash
python3 src/main.py                          # Entrega 1 con los datos reales: genera el Silver y el Gold
scripts/e2_postgres.sh iniciar               # Postgres local en 127.0.0.1:5434 (detener | estado)
python3 src/main.py --entrega 2              # todos los pasos de la Entrega 2
python3 src/main.py --entrega 2 --lista      # lista los pasos
python3 src/main.py --entrega 2 --desde indexar
python3 src/main.py --entrega 2 --solo temas modelo   # solo estos pasos
```

Sin documentos ni llave se pueden correr solo `temas` y `modelo`, que usan el catálogo versionado y el Gold de la Entrega 1 (con datos ficticios basta). Los pasos `catalogo`, `transcribir`, `indexar`, `evaluar`, `entropia` y `agente` necesitan los documentos y la llave, y los últimos cuatro, además, Postgres iniciado.

Los pasos que llaman al modelo guardan lo que producen (`data/plata/documentos/transcripciones/`, `artifacts/entrega2/resultados/`) y no repiten lo ya hecho. Para volver a responder y calificar: `python3 src/entrega2/evaluar.py --rehacer`.

Consultar el agente:

```bash
python3 src/entrega2/agente.py "El programa menciona tutorías grupales. ¿Se siguen ofreciendo?"
```

| Paso | Script | Qué hace |
|---|---|---|
| `catalogo` | `src/entrega2/catalogo.py` | Propone `data/plata/documentos/catalogo_documentos.csv`: una fila por documento con semestre, vigencia y nivel. Se corrige a mano y es la fuente de las etiquetas |
| `transcribir` | `src/entrega2/transcribir.py` | Ingesta visual: renderiza cada página y un modelo con visión la transcribe (texto, código de las capturas, tablas y figuras) |
| `indexar` | `src/entrega2/indexar.py` | Chunking por página, embeddings (`multilingual-e5-small`) y carga en pgvector. Dos colecciones: `texto` (capa de texto del PDF) y `visual` (transcripciones) |
| `bodega` | `src/entrega2/bodega.py` | Copia el Gold de la Entrega 1 en `data/oro/bookeau_agente.sqlite3`, retira los comentarios de texto libre, añade `agg_tipos_de_horario` y `agg_oferta_periodo` (de `data/oro/oferta_por_periodo.csv`), comprueba que la oferta por franja de `hecho_oferta` cuadre con ella y crea las vistas que consulta el agente. Si el Gold se construyó sin los horarios, el agente usa `agg_demanda_franja` (regla R05), sin capacidad por franja |
| `evaluar` | `src/entrega2/evaluar.py` | Responde 26 preguntas con prompting directo, RAG de texto y RAG visual, y las califica con un modelo juez |
| `entropia` | `src/entrega2/poc_entropia.py` | Prueba de concepto con las dos versiones del programa del curso (2020-20 y 2026-20) |
| `agente` | `src/entrega2/casos_agente.py` | Casos del agente híbrido |
| `figuras` | `src/auxiliar/e2_figuras.py` | Gráficas del informe |
| `temas` | `src/auxiliar/e2_temas_por_nivel.py` | Qué clases de 2026-20 tienen versión en el material de 2020-21; tabla del informe |
| `poster` | `src/auxiliar/e2_figuras_poster.py` | Gráficas y recortes de documentos del póster, al tamaño de impresión |
| `modelo` | `src/auxiliar/e2_modelo_dimensional.py` | Diagrama del modelo dimensional para el póster; se detiene si no coincide con el DDL de `sql/e2_bodega_modelo_gold.sql` |

Los enfoques están en `src/entrega2/enfoques.py`, el acceso a la base vectorial en `base_vectorial.py`, el juez en `juez.py` y las llamadas al modelo, con su registro de tokens y tiempo, en `llm.py`. Los cuatro últimos pasos solo producen material del informe y del póster, por eso viven en `src/auxiliar/`.

### Datos de la Entrega 2

| Dato | Dónde | ¿Se versiona? |
|---|---|---|
| Documentos vigentes (2026-20): programa y 44 presentaciones | `data/bronce/documentos/vigentes/` | No: material del curso con derechos reservados de la Universidad |
| Documentos históricos (2020-20 y 2021-10): programa y 12 presentaciones | `data/bronce/documentos/historicos/` | No, por lo mismo |
| Banco de preguntas (evaluación, vigencia y agente) | `data/bronce/evaluacion/` | Sí |
| Catálogo de documentos | `data/plata/documentos/catalogo_documentos.csv` | Sí |
| Páginas renderizadas y transcripciones | `data/plata/documentos/paginas/`, `transcripciones/` | No: se derivan de los documentos |
| Oferta y ocupación por semestre (de la Entrega 1) | `data/oro/oferta_por_periodo.csv` | Sí |
| Copia de la bodega para el agente | `data/oro/bookeau_agente.sqlite3` | No: datos de estudiantes |
| Resultados, figuras, tablas y gráficas del póster | `artifacts/entrega2/` | No: se generan al ejecutar |

Las trazas de los tres primeros intentos del caso 8 del agente, que el código actual ya no reproduce, se guardan junto al informe en `docs/entregables/e2_informe/ag-08_intentos_previos.json`.

### Decisiones de diseño

- **La página es la unidad de chunking.** Una diapositiva es una idea. Solo se parten las páginas de más de 200 palabras (las del programa), entre líneas para no romper código ni tablas.
- **La visión se usa al ingerir, no al buscar.** Las presentaciones llevan el código como capturas de pantalla y el programa 2020-20 es un escaneo sin capa de texto. Transcribir cada página una vez permite seguir usando embeddings de texto y el esquema de pgvector del laboratorio del curso.
- **Semestre, vigencia y nivel son columnas del documento.** Son los filtros que controlan qué versión puede recuperar el RAG, así que viven en `documentos` y no en un JSONB.
- **El agente consulta vistas, no las tablas del modelo dimensional.** Las vistas resuelven los joins y nombran las columnas de forma que el modelo escriba SQL correcto. La conexión es de solo lectura, admite una sola sentencia `SELECT` y corta las consultas largas.
- **Lo que sale hacia el modelo externo no lleva datos personales.** La copia de la bodega no tiene los comentarios abiertos de las encuestas, `dim_programa` está vedada y las portadas de las presentaciones históricas (nombre y correo de quien dictó la sección) se omiten.

### Recompilar informes y póster

Los PDF ya están versionados; solo hace falta recompilarlos si cambias el texto o los datos.

| Producto | Requisitos | Comando |
|---|---|---|
| Informe y anexos de la Entrega 1 | TeX Live o MacTeX (distribución completa) | `cd docs/entregables/e1_informe && pdflatex informe_latex.tex` (dos veces, para las referencias); igual con `anexos_latex.tex`. Las imágenes están en `img/` |
| Informe de la Entrega 2 | TeX Live o MacTeX; usa `fontspec`, así que se compila con **XeLaTeX o LuaLaTeX**, no con `pdflatex` | Antes, generar figuras y tabla: `python3 src/main.py --entrega 2 --solo figuras temas` (necesita los resultados de `evaluar`, `entropia` y Postgres; ver arriba). Luego `cd docs/entregables/e2_informe && xelatex informe.tex` (dos veces). Lee `artifacts/entrega2/figuras/` y `artifacts/entrega2/tablas/` |
| Póster de la Entrega 2 | Chrome o Chromium y `pdfinfo` (poppler: `brew install poppler`) | `python3 src/main.py --entrega 2 --solo poster modelo` (el paso `poster` necesita las páginas renderizadas por `transcribir` y los resultados de `evaluar`), luego `src/auxiliar/e2_exportar_poster.sh` (fuera de macOS, `CHROME=/ruta/al/navegador src/auxiliar/e2_exportar_poster.sh`). `src/auxiliar/e2_medir_poster.sh` dice cuántos milímetros sobran o faltan en cada columna |

La fuente Helvetica Neue, con la que se miden las cajas del diagrama del modelo, solo existe en macOS; en otros sistemas el paso `modelo` usa una medida aproximada y el diagrama puede variar un poco.

## Estructura

```
data/          bronce/ → plata/ → oro/ (arquitectura medallón, compartida por las dos entregas)
docs/          documentacion/ (enunciados e1_, e2_), entregables/ (e1_informe, e1_tablero, e2_informe, e2_poster)
src/           main.py (punto de entrada), entrega1/, entrega2/, auxiliar/ (código de informe y póster, prefijo e2_)
sql/           DDL y consultas (prefijo e1_, e2_)
scripts/       e2_postgres.sh
notebooks/     cuadernos de la Entrega 1 (prefijo e1_)
artifacts/     todo lo generado en ejecución: entrega1/ y entrega2/ (no se versiona)
```

| Carpeta | Contenido |
|---|---|
| `data/bronce/dummy/` | E1: Excel ficticios (reservas, cuatro encuestas y horarios). **Sí se versionan** |
| `data/bronce/Bookeau/` | E1: Excel originales. **No se versiona** (datos personales) |
| `data/bronce/documentos/` | E2: PDF del curso, `vigentes/` e `historicos/`. **No se versiona** (derechos reservados) |
| `data/bronce/evaluacion/` | E2: banco de preguntas escrito a mano |
| `data/plata/` | E1: Silver, 6 CSV limpios con trazabilidad y banderas (se genera). E2: `documentos/` con el catálogo (versionado), páginas y transcripciones (se generan) |
| `data/oro/` | E1: Gold, dimensiones, hechos y `bookeau.sqlite3` (se genera). E2: `oferta_por_periodo.csv` (versionado) y `bookeau_agente.sqlite3` (se genera) |
| `src/main.py` | Punto de entrada: `--entrega 1` (por defecto) o `--entrega 2` |
| `src/entrega1/` | Pipeline de la Entrega 1 (`main.py` y un script por paso), generador de datos ficticios y `plantillas/` del tablero |
| `src/entrega2/` | Núcleo de la Entrega 2: catálogo, transcripción, índice, bodega, enfoques, juez, evaluación, entropía y agente |
| `src/auxiliar/` | Código que solo produce material del informe y del póster (`e2_figuras.py`, `e2_figuras_poster.py`, `e2_temas_por_nivel.py`, `e2_modelo_dimensional.py`, `e2_exportar_poster.sh`, `e2_medir_poster.sh`) |
| `sql/` | E1: DDL del modelo Gold y consultas de los análisis. E2: esquema de la base vectorial, modelo y vistas de la bodega del agente |
| `scripts/` | `e2_postgres.sh`: Postgres local para la base vectorial |
| `notebooks/` | Cuadernos de la Entrega 1: exploración, caracterización, calidad, limpieza y Gold |
| `docs/documentacion/` | Enunciados de las dos entregas, plan de la Entrega 1 y README de la fuente Bookeau |
| `docs/entregables/` | `e1_informe/` (informe y anexos; en `img/`, diagramas del ecosistema y del modelo y capturas del tablero), `e1_tablero/` (tablero interactivo), `e2_informe/` (informe), `e2_poster/` (póster) |
| `artifacts/entrega1/` | Salidas del pipeline: caracterización, calidad, limpieza, transformación, análisis (no se versiona) |
| `artifacts/entrega2/` | Resultados de las corridas, figuras y tabla del informe y gráficas del póster |

## Modelo en Gold

Esquema dimensional de Kimball con cuatro tablas de hechos (`hecho_reserva`, `hecho_encuesta`, `hecho_respuesta`, `hecho_oferta`) y diez dimensiones (`dim_fecha`, `dim_periodo`, `dim_dia_semana`, `dim_hora`, `dim_servicio`, `dim_modalidad`, `dim_estado`, `dim_programa`, `dim_tipo_encuesta`, `dim_pregunta`). `hecho_oferta` tiene grano período × día de la semana × hora de inicio y se cruza con las reservas por período y hora. Las reglas de negocio viven en las dimensiones: `dim_estado` guarda el estado original, el analítico (R01, R06 y R07) y el grupo de estado (R04), con «Cola a reserva» como grupo propio. La definición completa está en [`sql/e1_00_crear_modelo.sql`](sql/e1_00_crear_modelo.sql) y las consultas de los análisis en [`sql/e1_01_consultas_analisis.sql`](sql/e1_01_consultas_analisis.sql).

## Notas

- Los comentarios de texto libre están en Gold (`hecho_respuesta`), pero su análisis queda para las siguientes entregas.
- Las capturas del tablero (`docs/entregables/e1_informe/img/tablero_*.png`) se tomaron con Chrome sin interfaz del tablero generado con los datos reales.
- `requirements.txt` está comentado por entrega: la Entrega 1 solo necesita sus paquetes para los cuadernos; la Entrega 2 los necesita todos.
