# Inventario inicial · Bookeau

Inventario de los 114 archivos Excel extraídos de `data/bronce/Bookeau.zip`. Se conserva el ZIP original y la estructura de carpetas de la fuente. Los metadatos de macOS no se extrajeron.

| Grupo | Archivos | Hojas | Filas de datos | Variables por hoja | Períodos |
|---|---:|---:|---:|---|---|
| Encuesta Express | 29 | 29 | 6,759 | 33 | 201620–202610 (29) |
| Encuesta Normal | 29 | 29 | 16,379 | 35 | 201620–202610 (29) |
| Encuesta Reserva Express | 14 | 14 | 13,815 | 22 | 201920–202610 (14) |
| Encuesta Reserva Normal IP | 13 | 13 | 23,437 | 22 | 201920–202610 (13) |
| Reservas | 29 | 29 | 86,562 | 17 | 201620–202610 (29) |

Total: **146,952 filas** entre todas las hojas, antes de depurar o unir fuentes.

## Método y límites

Se cuentan filas con contenido de celda en cada hoja; la primera fila con contenido se interpreta como encabezado y se excluye del conteo. El número de variables corresponde a las celdas no vacías del encabezado. Estos conteos no establecen unicidad, número de reservas distintas ni cantidad de estudiantes. Una reserva puede aparecer también en varias encuestas, por lo que no se deben sumar fuentes para calcular reservas únicas.

El detalle por archivo, hoja, período y columnas está en `inventario_fuentes.csv`.

## Observaciones para la exploración

- La fuente corresponde a tutorías de CupiTaller gestionadas con Bookeau.
- Hay reservas y encuestas previas y posteriores para tutorías Express y Normal.
- Los encabezados de satisfacción incluyen comentarios y observaciones de texto libre; revisar contenido y cobertura para las siguientes entregas.
- La cantidad de variables y la cobertura temporal de las encuestas requieren revisión antes de concatenar archivos.
- El README de origen menciona cobertura general desde 201620 hasta 202610, pero las encuestas previas tienen menos archivos; usar el inventario real para documentar la cobertura.
- En las muestras, reservas utiliza `Código servicio`, mientras encuestas utiliza `Código del servicio`; documentar la homologación.

## Siguiente paso

Perfilar las fuentes, identificar las claves de reserva y contrastar dos análisis candidatos: demanda/asistencia de tutorías y satisfacción de estudiantes. Confirmar objetivos y roles antes de fijar el modelo.
