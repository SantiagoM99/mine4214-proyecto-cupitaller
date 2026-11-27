# Resumen de la Entrega 1 · MINE-4214 · Reservas y satisfacción en CupiTaller

Fuente de este resumen: el repositorio `mine4214-proyecto-cupitaller` (código en `src/entrega1/`, evidencia de la última corrida con datos reales en `artifacts/entrega1/` y su copia en `docs/artifacts/`, y los CSV de `data/plata/` y `data/oro/` del 26-nov-2026). Las cifras son de los datos reales de Bookeau, no de los ficticios.

## 1. Qué se entregó

| Producto | Ruta |
|---|---|
| Enunciado | `docs/enunciados/e1_enunciado_entrega_1.pdf` (y `.txt`) |
| Informe (LaTeX y PDF) | `docs/entregables/e1_informe/informe_latex.tex`, `informe_latex.pdf` |
| Anexos (glosario, datos de apoyo, extensión de texto) | `docs/entregables/e1_informe/anexos_latex.tex`, `anexos_latex.pdf` |
| Diagramas y capturas del informe | `docs/entregables/e1_informe/img/` (ecosistema, modelos de reserva, oferta y encuesta, tres capturas del tablero) |
| Tablero interactivo (HTML sin servidor) | `docs/entregables/e1_tablero/tablero_bookeau.html` (la versión versionada es la de datos ficticios) |
| Pipeline (8 pasos, solo biblioteca estándar de Python) | `src/main.py` → `src/entrega1/main.py` |
| DDL del modelo Gold y consultas de los análisis | `sql/e1_00_crear_modelo.sql`, `sql/e1_01_consultas_analisis.sql` |
| Cuadernos | `notebooks/e1_00_exploracion…`, `e1_01_caracterizacion…`, `e1_02_calidad_y_analisis…`, `e1_03_limpieza…`, `e1_04_modelo_y_gold_bookeau.ipynb` |
| Evidencia generada | `artifacts/entrega1/{caracterizacion, calidad, limpieza, transformacion, analisis}/` |
| Datos ficticios para reproducir sin datos personales | `data/bronce/dummy/` (45 Excel) y `src/entrega1/generar_datos_dummy.py` |

Pasos del pipeline (`src/entrega1/main.py`): `caracterizar` → `documentar` → `preparar` → `limpiar` → `horarios` → `comprobar` → `gold` → `tablero`.

### Análisis que responde

1. **Inasistencia, presión de cola y oferta** (coordinación de CupiTaller): tasa de inasistencia, proporción de solicitudes en cola, ocupación de la oferta, lista de espera y conversión de cola a reserva, por modalidad, día, hora y período.
2. **Satisfacción** (coordinación académica): proporción de calificaciones 1–3 por modalidad, servicio y período, con media y distribución de apoyo.

Resultados globales (`artifacts/entrega1/analisis/resumen.json`): 83.894 eventos de reserva, 41.430 atenciones, tasa de inasistencia 10,5 %, proporción en cola 12,1 %, ocupación de la oferta 74,5 % (capacidad 46.867), conversión de cola a reserva 34,5 %, 16.050 calificaciones utilizables con media 4,74 y 5,7 % de calificaciones bajas.

## 2. Volumen de datos

### Bronze (`data/bronce/Bookeau/`, Excel sin modificar, 2016-20 a 2026-19)

| Fuente | Archivos | Filas | Variables | Tamaño aprox. |
|---|---:|---:|---:|---:|
| Reservas | 29 | 86.562 | 17 | ≈ 63 MB |
| Encuesta Express (satisfacción, tutoría 30 min) | 29 | 6.759 | 33 | ≈ 11 MB |
| Encuesta Normal (satisfacción, tutoría 1 h) | 29 | 16.379 | 35 | ≈ 26 MB |
| Encuesta Reserva Express (previa) | 14 | 13.815 | 22 | ≈ 13 MB |
| Encuesta Reserva Normal IP (previa) | 13 | 23.437 | 22 | ≈ 22 MB |
| Horarios (oferta por franja, sin datos personales) | 30 | 1.396 | — | ≈ 0,8 MB |
| **Total** | **144** | **148.348** | | |

Fuentes: `artifacts/entrega1/caracterizacion/resumen_grupos.csv` y `archivos.csv`, `artifacts/entrega1/limpieza/horarios_archivos.csv`. En las cinco fuentes de reservas y encuestas el ID es único y completo (0 faltantes, 0 duplicados exactos) y cada grupo tiene un solo esquema de encabezados. Tres libros de horarios (202219, 202220 y 202319) vienen vacíos. La carpeta `data/bronce/` también guarda los documentos y el banco de preguntas de la Entrega 2 (≈165 MB en total).

### Silver (`data/plata/`, 6 CSV)

| Archivo | Filas | Columnas | Tamaño |
|---|---:|---:|---:|
| `reservas.csv` | 86.562 | 26 | 31,0 MB |
| `encuesta_satisfaccion_express.csv` | 6.759 | 49 | 3,6 MB |
| `encuesta_satisfaccion_normal.csv` | 16.379 | 51 | 9,7 MB |
| `encuesta_previa_express.csv` | 13.815 | 36 | 6,8 MB |
| `encuesta_previa_normal_ip.csv` | 23.437 | 36 | 11,6 MB |
| `horarios.csv` | 1.396 | 16 | 0,15 MB |

### Gold (`data/oro/`, CSV por tabla y `bookeau.sqlite3` de 74,6 MB)

| Tabla | Filas | Grano |
|---|---:|---|
| `hecho_reserva` | 83.894 | una reserva de tutoría |
| `hecho_encuesta` | 60.024 | una encuesta válida ligada a una reserva en Gold |
| `hecho_respuesta` | 383.183 | una respuesta no vacía a una pregunta de una encuesta |
| `hecho_oferta` | 1.396 | período × día de la semana × hora de inicio |
| `dim_fecha` / `dim_hora` | 3.565 / 1.440 | día / minuto |
| `dim_periodo` / `dim_dia_semana` | 30 / 7 | |
| `dim_servicio` / `dim_modalidad` / `dim_estado` | 8 / 15 / 13 | |
| `dim_programa` / `dim_tipo_encuesta` / `dim_pregunta` | 164 / 4 / 22 | |

Fuente: `artifacts/entrega1/transformacion/controles_gold.json` (coincide con el conteo de los CSV).

## 3. Capas y transformaciones

### Bronze → Silver (`src/entrega1/limpiar_bookeau.py` y `procesar_horarios.py`)

Principio: reglas mecánicas y documentadas, **sin eliminar filas ni imputar respuestas** (filas Bronze = filas Silver en los cinco grupos; `limpieza/controles_carga.csv`).

- **Esquema**: se exige un único esquema por grupo y se renombran las columnas a nombres canónicos (`limpieza/diccionario_columnas.csv`).
- **Nulos**: celdas vacías o con solo espacios pasan a nulo (conteos por columna en `limpieza/bitacora_transformaciones.csv`).
- **Fechas**: fechas de Excel a ISO 8601 (fecha inicio, fin y llegada); las no interpretables se marcan con bandera.
- **Programa**: se normaliza en una columna adicional (`programa_normalizado`) y se conserva el original (`limpieza/mapa_programas.csv`); por ejemplo, en Reservas 213 programas originales quedan en 174.
- **R01**: «Finalizada» y «Realizada» se agrupan como *Atendida* en `estado_reserva_analitico`; el estado original se mantiene.
- **R02**: las encuestas marcadas «Inválida» se marcan `incluir_encuesta_en_analisis = false` (53 Express, 111 Normal, 2 previa Normal); quedan en Silver para auditoría.
- **Campos derivados**: período de origen, `duracion_programada_minutos`, `es_prioritaria`.
- **Trazabilidad**: cada fila guarda `archivo_origen`, `hoja_origen` y `fila_excel`.
- **Banderas de calidad** en `banderas_calidad_json` (`limpieza/resumen_banderas.csv`): atributos de la encuesta que difieren de la reserva (761 en total), cancelaciones con hora de llegada (34), finalizadas sin llegada (14), no asistió con llegada (9). Casos de revisión en `limpieza/casos_revision.csv`.
- **Vínculo encuesta–reserva**: todas las encuestas encuentran su reserva, sin vínculos ambiguos ni diferencias de período.
- **Horarios**: hora en texto («9:00 am») a 24 h, día a ISO; se concilian con Reservas por franja y coinciden al 100 % en todos los períodos menos 202619, con 10 franjas que difieren (`calidad/reconciliacion_horarios_reservas.csv`, `reconciliacion_horarios_detalle.csv`).

### Silver → Gold (`src/entrega1/construir_gold_bookeau.py`, DDL en `sql/e1_00_crear_modelo.sql`)

Modelo dimensional de Kimball con 4 hechos y 10 dimensiones, cargado en SQLite. Reglas aplicadas:

- **R03**: solo reservas de tutoría (tipo de horario Normal, Express o Normal pico). Se excluyen 2.668 reservas (86.562 → 83.894) y 200 encuestas cuyas reservas no son tutorías.
- **R02**: entran solo encuestas válidas y cuya reserva esté en Gold (166 excluidas por R02).
- **R06**: los cinco estados de cancelación se agrupan en «Cancelada».
- **R07**: los estados abiertos se cierran: «En ejecución» es Atendida; «Reservada» es Atendida con hora de llegada y prestador, y No asistió en los demás casos.
- **R04**: se materializa en `dim_estado.grupo_estado` (Atendida, No asistió, Cancelada, Cola, Cola a reserva). La cola no ocupa cupo, y «Cola cancelada por reservación» se reporta aparte.
- **R05**: la oferta (horarios, solo «Tutor Presencial») carga `hecho_oferta` y se cruza con las reservas por período y hora.
- **Encuestas**: todas sus dimensiones se toman de la reserva enlazada; las diferencias con la fuente quedan en `diferencias_con_reserva_json`.
- **Respuestas**: las encuestas pasan de formato ancho a largo en `hecho_respuesta` (una fila por pregunta respondida, con valor original y numérico).
- **Claves**: claves sustitutas para todas las dimensiones; el período académico vive solo en `dim_periodo`.

Controles de validación (`transformacion/controles_gold.json` y `conciliacion_silver_gold.csv`): integridad de claves foráneas OK, unicidad de los granos OK y conciliación de conteos Silver = Gold + excluidas OK. Por ejemplo, Encuesta Normal: 16.379 en Silver = 16.181 en Gold + 111 (R02) + 87 (R03).

| Encuestas | Silver | Gold | Excluidas R02 | Excluidas R03 |
|---|---:|---:|---:|---:|
| Express | 6.759 | 6.646 | 53 | 60 |
| Normal | 16.379 | 16.181 | 111 | 87 |
| Previa Express | 13.815 | 13.815 | 0 | 0 |
| Previa Normal IP | 23.437 | 23.382 | 2 | 53 |
