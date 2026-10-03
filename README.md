# Proyecto MINE-4214 · Reservas y satisfacción en CupiTaller

Proyecto del curso Modelado y Diseño de Datos (Uniandes, 2026-2) sobre las reservas de tutoría y las encuestas de estudiantes de CupiTaller, exportadas de Bookeau (2016–2026).

## Entrega 1

| Producto | Archivo |
|---|---|
| **Informe (PDF)** | [`entregables/informe_entrega_1.pdf`](entregables/informe_entrega_1.pdf) |
| Informe (fuente Markdown) | [`entregables/informe_entrega_1.md`](entregables/informe_entrega_1.md) |
| Tablero interactivo (abrir en el navegador, sin servidor) | [`entregables/tablero_bookeau.html`](entregables/tablero_bookeau.html) |
| Enunciado | [`docs/Proyecto - entrega 1.pdf`](docs/Proyecto%20-%20entrega%201.pdf) |

**Pendiente del equipo antes de entregar:** completar integrantes y la sección 7.a del informe; validar con la coordinación el supuesto D1 (definición de inasistencia y cola); regenerar el PDF.

## Análisis

1. **Inasistencia y presión de cola** (coordinación de CupiTaller): tasa de inasistencia = No asistió / (Atendida + No asistió); proporción de solicitudes en cola. Por modalidad, día, hora y período.
2. **Satisfacción** (coordinación académica): proporción de calificaciones 1–3 por modalidad, servicio y período, con la media y la distribución como apoyo.

Reglas: **R01** Finalizada + Realizada = Atendida · **R02** se excluyen las encuestas «Inválida» · **D1** la cola no ocupa cupo (supuesto por validar).

## Estructura

| Carpeta | Contenido |
|---|---|
| `data/` | Bronze, Silver y Gold. **No se versiona** (datos personales); ver [`data/README.md`](data/README.md) |
| `src/` | Pipeline y generadores (Python estándar, salvo figuras y PDF) |
| `src/plantillas/` | Plantillas HTML de los tableros |
| `sql/` | DDL del modelo Gold y consultas de los análisis |
| `notebooks/` | Cuadernos ejecutados: exploración, caracterización, calidad, limpieza, Gold |
| `docs/` | Evidencia: caracterización, calidad, limpieza, reglas, modelo, transformación, análisis |
| `img/` | Diagramas y capturas usados en el informe |
| `entregables/` | Informe y tablero |
| `exploratorio/` | Explorador de comentarios por monitor. **No se versiona ni se entrega**: contiene nombres y comentarios, y el clasificador no está validado |

## Reproducción

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python src/caracterizar_bookeau.py        # perfilamiento de Bronze
python src/documentar_caracterizacion.py  # diccionario y documento de caracterización
python src/preparar_analisis_bookeau.py   # evidencia de calidad para los análisis
python src/limpiar_bookeau.py             # Bronze → Silver
python src/comprobar_estados_encuestas.py # cruce estados de reserva × encuestas
python src/construir_gold_bookeau.py      # Silver → Gold + controles
python src/generar_tablero_bookeau.py     # tablero
python src/generar_figuras.py             # diagramas del informe
python src/generar_informe_pdf.py         # informe PDF (requiere Google Chrome)
```

Las capturas del tablero (`img/tablero_*.png`) se tomaron con Chrome sin interfaz desde `entregables/tablero_bookeau.html`.

## Documentación de apoyo

- [README de la fuente Bookeau](docs/fuente_bookeau_README.md) · [Inventario](docs/inventario_fuentes.md)
- [Caracterización](docs/caracterizacion/caracterizacion_bookeau.md) · [Diccionario de variables](docs/caracterizacion/diccionario_variables.md)
- [Calidad para los análisis](docs/calidad/evaluacion_para_analisis.md) · [Estados vs. encuestas](docs/calidad/estados_encuestas/comprobacion.md)
- [Limpieza Silver](docs/limpieza/README.md) · [Reglas de negocio](docs/limpieza/reglas_negocio.md)
- [Ecosistema](docs/arquitectura/ecosistema_analitica.md) · [Modelo dimensional](docs/modelo/modelo_dimensional.md) · [Silver → Gold](docs/transformacion/proceso_silver_gold.md)
- [Definición de análisis](docs/analisis/definicion_analisis.md) · [Resultados](docs/analisis/respuestas_analisis.md)
- Análisis de texto (siguientes entregas): [método y límites](docs/texto/README.md)
