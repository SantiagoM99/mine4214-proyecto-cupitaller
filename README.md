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

## Ejecutar el proyecto

Los datos reales no se distribuyen (contienen datos personales). El repositorio incluye **datos ficticios** con la misma estructura en `data/bronce/dummy/`, con los que se puede ejecutar todo el flujo.

**Requisito:** Python 3.10 o superior. El pipeline usa solo la biblioteca estándar; no hay que instalar nada para ejecutarlo.

### Inicio rápido con datos ficticios

Desde la raíz del repositorio:

```bash
python3 src/main.py --dummy
```

Tarda menos de un segundo y ejecuta los 8 pasos de Bronze a Gold. Al terminar:

| Resultado | Dónde |
|---|---|
| Silver (6 CSV) | `data/plata/` |
| Gold: base SQLite con el modelo dimensional | `data/oro/bookeau.sqlite3` (más un CSV por tabla) |
| Controles de conciliación e integridad | `docs/artifacts/transformacion/controles_gold.json` |
| Evidencia de caracterización, calidad y limpieza | `docs/artifacts/` |
| Tablero | `docs/entregables/tablero_bookeau.html` (abrir en el navegador) |

Para consultar el modelo directamente: `sqlite3 data/oro/bookeau.sqlite3 < sql/01_consultas_analisis.sql`.

Con datos ficticios los conteos son pequeños (≈1.700 reservas) y **no coinciden con las cifras del informe**, que se calcularon con los datos reales (83.894 reservas de tutoría). El tablero versionado en `docs/entregables/` es el generado con los datos ficticios; las capturas del informe (`docs/img/tablero_*.png`) son del tablero con los datos reales.

### Opciones de `main.py`

```bash
python3 src/main.py --dummy                    # todo el flujo con datos ficticios
python3 src/main.py --dummy --regenerar-dummy  # vuelve a generar los Excel ficticios antes de ejecutar
python3 src/main.py                            # datos reales en data/bronce/Bookeau/ (ver data/README.md)
python3 src/main.py --lista                    # lista los pasos
python3 src/main.py --dummy --desde gold       # retoma desde un paso
python3 src/main.py --dummy --solo gold tablero
```

Cada ejecución sobrescribe `data/plata/`, `data/oro/`, `docs/artifacts/` y el tablero.

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

### Cuadernos

Los cuadernos de `notebooks/` leen los resultados del pipeline, así que primero hay que ejecutar `python3 src/main.py --dummy`. Requieren Jupyter:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab notebooks/
```

Las salidas guardadas en los cuadernos corresponden a los datos ficticios.

### Datos reales

Quien tenga acceso a `Bookeau.zip` (compartido por la coordinación de CupiTaller) lo descomprime como `data/bronce/Bookeau/` y ejecuta `python3 src/main.py`. Ver [`data/README.md`](data/README.md).

## Estructura

| Carpeta | Contenido |
|---|---|
| `data/bronce/dummy/` | Excel ficticios (reservas, cuatro encuestas y horarios). **Sí se versionan** |
| `data/bronce/Bookeau/` | Excel originales. **No se versiona** (datos personales) |
| `data/plata/` | Silver: 6 CSV limpios, con trazabilidad y banderas. Se genera al ejecutar |
| `data/oro/` | Gold: dimensiones, hechos y base SQLite `bookeau.sqlite3`. Se genera al ejecutar |
| `src/` | Pipeline (`main.py` y un script por paso) y generador de datos ficticios (`generar_datos_dummy.py`) |
| `src/plantillas/` | Plantilla HTML del tablero |
| `sql/` | DDL del modelo Gold y consultas de los análisis |
| `notebooks/` | Cuadernos: exploración, caracterización, calidad, limpieza y Gold |
| `docs/documentacion/` | Enunciado, plan de la entrega y README de la fuente Bookeau |
| `docs/entregables/` | Informe y anexos (LaTeX y PDF) y tablero |
| `docs/img/` | Diagramas del ecosistema y del modelo, y capturas del tablero (ya generados) |
| `docs/artifacts/` | Salidas del pipeline (caracterización, calidad, limpieza, transformación y resultados). Se genera al ejecutar |

## Modelo en Gold

Esquema dimensional de Kimball con cuatro tablas de hechos (`hecho_reserva`, `hecho_encuesta`, `hecho_respuesta`, `hecho_oferta`) y diez dimensiones (`dim_fecha`, `dim_periodo`, `dim_dia_semana`, `dim_hora`, `dim_servicio`, `dim_modalidad`, `dim_estado`, `dim_programa`, `dim_tipo_encuesta`, `dim_pregunta`). `hecho_oferta` tiene grano período × día de la semana × hora de inicio y se cruza con las reservas por período y hora. Las reglas de negocio viven en las dimensiones: `dim_estado` guarda el estado original, el analítico (R01, R06 y R07) y el grupo de estado (R04), con «Cola a reserva» como grupo propio. La definición completa está en [`sql/00_crear_modelo.sql`](sql/00_crear_modelo.sql) y las consultas de los análisis en [`sql/01_consultas_analisis.sql`](sql/01_consultas_analisis.sql).

## Notas

- Los comentarios de texto libre están en Gold (`hecho_respuesta`), pero su análisis queda para las siguientes entregas.
- Las capturas del tablero (`docs/img/tablero_*.png`) se tomaron con Chrome sin interfaz del tablero generado con los datos reales.
- Las dependencias de `requirements.txt` solo hacen falta para los cuadernos.
