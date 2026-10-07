# Proyecto MINE-4214 · Reservas y satisfacción en CupiTaller

Proyecto del curso Modelado y Diseño de Datos (Uniandes, 2026-2) sobre las reservas de tutoría y las encuestas de estudiantes de CupiTaller, exportadas de Bookeau (2016–2026). Parte de los datos en Excel y construye un lakehouse por capas (Bronze, Silver y Gold), un modelo dimensional y un tablero que responde dos análisis.

## Entrega 1

| Producto | Archivo |
|---|---|
| **Informe** (LaTeX y PDF) | [`docs/entregables/latex/informe_latex.pdf`](docs/entregables/latex/informe_latex.pdf) |
| **Anexos** del informe (glosario, datos de apoyo, extensión de texto) | [`docs/entregables/latex/anexos_latex.pdf`](docs/entregables/latex/anexos_latex.pdf) |
| Tablero interactivo (abrir en el navegador, sin servidor) | [`docs/entregables/tablero_bookeau.html`](docs/entregables/tablero_bookeau.html) |



## Análisis

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

## Ejecutar el pipeline

Con Python 3.10 o superior; el pipeline usa solo la biblioteca estándar.

```bash
# Crear ambiente
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt       

# Ejecutar pipeline
python3 src/main.py            # datos reales (data/bronce/Bookeau/)
python3 src/main.py --dummy    # datos ficticios, para probar el flujo completo
python3 src/main.py --lista    # pasos disponibles; también --desde PASO y --solo PASO...
```

`main.py` ejecuta los pasos en este orden y se detiene si uno falla:

| Paso | Script | Qué hace |
|---|---|---|
| `caracterizar` | `src/caracterizar_bookeau.py` | Perfilamiento de Bronze |
| `documentar` | `src/documentar_caracterizacion.py` | Diccionario y documento de caracterización |
| `preparar` | `src/preparar_analisis_bookeau.py` | Evidencia de calidad para los análisis |
| `limpiar` | `src/limpiar_bookeau.py` | Bronze → Silver |
| `horarios` | `src/procesar_horarios.py` | Horarios (oferta) Bronze → Silver, y conciliación con Reservas por franja |
| `comprobar` | `src/comprobar_estados_encuestas.py` | Cruce de estados de reserva y encuestas |
| `gold` | `src/construir_gold_bookeau.py` | Silver → Gold, con controles de integridad y conciliación |
| `tablero` | `src/generar_tablero_bookeau.py` | Tablero HTML y resultados agregados |

### Datos reales y datos ficticios

Los datos reales contienen nombres, correos y códigos de estudiantes y monitores, así que **no se versionan**. Para reproducir con ellos, copiar `Bookeau.zip` (compartido por la coordinación) en `data/bronce/` y descomprimirlo como `data/bronce/Bookeau/`; ver [`data/README.md`](data/README.md).

Para probar el flujo sin datos personales, `--dummy` genera libros de Excel inventados con la misma estructura (`src/generar_datos_dummy.py`, en `data/bronce/dummy/`) y ejecuta todo el pipeline sobre ellos. 

## Estructura

| Carpeta | Contenido |
|---|---|
| `data/bronce/` | Excel originales sin modificar. **No se versiona** (excepto los Excel de `dummy/`) |
| `data/plata/` | Silver: 5 archivos CSV limpios, con trazabilidad y banderas. **No se versiona** |
| `data/oro/` | Gold: dimensiones, hechos y base SQLite `bookeau.sqlite3`. **No se versiona** |
| `data/bronce/dummy/` | Excel ficticios para probar el flujo con `--dummy`. Sí se versionan |
| `src/` | Pipeline (`main.py` y un script por paso) y generador de datos ficticios |
| `src/plantillas/` | Plantilla HTML del tablero |
| `src/auxiliar/` | Scripts que no son parte del pipeline: `generar_figuras.py` dibuja los diagramas del informe en `docs/img/` (requiere matplotlib) |
| `sql/` | DDL del modelo Gold y consultas de los análisis |
| `notebooks/` | Cuadernos: exploración, caracterización, calidad, limpieza y Gold |
| `docs/documentacion/` | Enunciado, plan de la entrega y README de la fuente Bookeau |
| `docs/entregables/` | Informe, anexos (LaTeX y PDF) y tablero |
| `docs/img/` | Diagramas del ecosistema y del modelo, y capturas del tablero |
| `docs/artifacts/` | Salidas generadas por el pipeline (caracterización, calidad, limpieza, transformación y resultados de los análisis). No se versiona |

## Modelo en Gold

Esquema dimensional de Kimball con cuatro tablas de hechos (`hecho_reserva`, `hecho_encuesta`, `hecho_respuesta`, `hecho_oferta`) y diez dimensiones (`dim_fecha`, `dim_periodo`, `dim_dia_semana`, `dim_hora`, `dim_servicio`, `dim_modalidad`, `dim_estado`, `dim_programa`, `dim_tipo_encuesta`, `dim_pregunta`). `hecho_oferta` tiene grano período × día de la semana × hora de inicio y se cruza con las reservas por período y hora. Las reglas de negocio viven en las dimensiones: `dim_estado` guarda el estado original, el analítico (R01, R06 y R07) y el grupo de estado (R04), con «Cola a reserva» como grupo propio. La definición completa está en [`sql/00_crear_modelo.sql`](sql/00_crear_modelo.sql) y las consultas de los análisis en [`sql/01_consultas_analisis.sql`](sql/01_consultas_analisis.sql).

## Notas

- Los comentarios de texto libre están en Gold (`hecho_respuesta`), pero su análisis queda para las siguientes entregas.
- Las capturas del tablero (`docs/img/tablero_*.png`) se tomaron con Chrome sin interfaz desde `docs/entregables/tablero_bookeau.html`.
- Las dependencias opcionales (`requirements.txt`: matplotlib, markdown, jupyter) solo hacen falta para las figuras (`python3 src/auxiliar/generar_figuras.py`), el PDF del informe en Markdown y los cuadernos.
