# Limpieza inicial · Bookeau · Capa Silver

## Resultado

Se generaron cinco CSV en `data/plata/` con las **146.952 filas de origen**, sin eliminar registros. Todos los grupos conservan ID completos y únicos; todas las encuestas se vinculan a una reserva del mismo período. La conciliación estructural es correcta en los cinco grupos; quedan cuestiones de calidad operativa pendientes.

| Fuente | Archivo Silver | Filas antes | Filas después | Registros con alguna bandera |
|---|---|---:|---:|---:|
| Encuesta Express | `encuesta_satisfaccion_express.csv` | 6,759 | 6,759 | 143 |
| Encuesta Normal | `encuesta_satisfaccion_normal.csv` | 16,379 | 16,379 | 427 |
| Encuesta Reserva Express | `encuesta_previa_express.csv` | 13,815 | 13,815 | 144 |
| Encuesta Reserva Normal IP | `encuesta_previa_normal_ip.csv` | 23,437 | 23,437 | 220 |
| Reservas | `reservas.csv` | 86,562 | 86,562 | 49 |

## Reglas aplicadas

| Regla | Resultado y evidencia |
|---|---|
| Nombres de columnas | Nombres comunes para los atributos, incluido codigo_servicio para ambos encabezados de origen. Las preguntas reciben nombres estables derivados de su texto completo; el diccionario conserva cada consigna. |
| Nulos | Celdas ausentes, vacías o solo espacios se exportan vacías. No aplica y otras respuestas textuales se mantienen como valores. |
| Fechas | Lectura con estilos y sistema de fechas Excel; exportación ISO 8601 con microsegundos. Las fechas no reciben una zona horaria inventada. |
| Identificadores | ID de reserva y códigos se serializan como texto; al cargar los CSV, declarar ese tipo. No se corrigen ni fusionan identidades. |
| Programas | Columna adicional programa_normalizado: mayúsculas, eliminación de tildes y compactación de espacios, incluidos espacios no separables. programa conserva el valor original no vacío. No se fusionan carreras por significado. |
| Prioridad | es_prioritaria nullable deriva true/false de sí/no; prioritaria_original conserva el valor exportado. |
| Calificación | Campo numérico adicional para valores enteros 1–5; campo original preservado; sin imputación de respuestas ausentes. |
| Trazabilidad | Cada fila conserva archivo, hoja, fila física Excel y período de origen. |
| Calidad | Banderas por fila para casos que requieren revisión; las encuestas mantienen sus propios atributos aunque difieran de Reservas. |

El cambio de formato de una fecha no crea información nueva. El programa normalizado solo homologa escritura; no es un catálogo académico certificado. Los textos libres, correos, nombres, estados originales y categorías históricas no se reescriben. La clasificación analítica adicional se documenta en `reglas_negocio.md`.

## Programas antes y después de normalizar escritura

| Fuente | Etiquetas originales no vacías | Etiquetas normalizadas no vacías |
|---|---:|---:|
| Encuesta Express | 131 | 109 |
| Encuesta Normal | 140 | 119 |
| Encuesta Reserva Express | 143 | 115 |
| Encuesta Reserva Normal IP | 122 | 91 |
| Reservas | 213 | 174 |

Consultar `mapa_programas.csv` para revisar cada correspondencia y su frecuencia. La reducción de etiquetas no representa reducción de personas ni certifica equivalencias entre titulaciones.

## Casos marcados para revisión

| Fuente | Bandera | Registros |
|---|---|---:|
| Encuesta Express | `atributos_difieren_de_reserva` | 88 |
| Encuesta Express | `encuesta_marcada_invalida_en_origen` | 53 |
| Encuesta Express | `revisar_finalizada_sin_llegada` | 2 |
| Encuesta Normal | `atributos_difieren_de_reserva` | 311 |
| Encuesta Normal | `encuesta_marcada_invalida_en_origen` | 111 |
| Encuesta Normal | `revisar_cancelacion_con_llegada` | 2 |
| Encuesta Normal | `revisar_finalizada_sin_llegada` | 4 |
| Encuesta Reserva Express | `atributos_difieren_de_reserva` | 144 |
| Encuesta Reserva Normal IP | `atributos_difieren_de_reserva` | 218 |
| Encuesta Reserva Normal IP | `encuesta_marcada_invalida_en_origen` | 2 |
| Reservas | `revisar_cancelacion_con_llegada` | 32 |
| Reservas | `revisar_finalizada_sin_llegada` | 8 |
| Reservas | `revisar_no_asistio_con_llegada` | 9 |

Un registro puede activar varias banderas; no sumar sus frecuencias como registros únicos. La tabla de resultado cuenta registros con al menos una bandera. `casos_revision.csv` permite localizar cada caso sin alterar el original.

Las 166 encuestas marcadas inválidas entre las cuatro fuentes se conservan en Silver, con `incluir_encuesta_en_analisis = false` según R02; quedan excluidas de indicadores y análisis de respuestas. Las diferencias con Reservas se documentan y no se resuelven sobrescribiendo atributos. Se añade `estado_reserva_analitico`: Finalizada y Realizada se agrupan como Atendida según R01, manteniendo la etiqueta original. Las etiquetas Deprecated conservan su tratamiento anterior.

La ausencia total de fecha de devolución se mantiene como limitación de la fuente: no se imputa con fecha fin. Los faltantes de llegada no se convierten automáticamente en No asistió.

## Controles ejecutados durante la carga

- Conteos de filas antes y después por archivo y grupo.
- Identificadores completos y unicidad por grupo.
- Existencia de reserva, vínculo inequívoco y coincidencia del período para encuestas.
- Coherencia inicio/fin y del año del período.
- Dominio de prioridad, calificación y estado de validez exportado.
- Consistencia de atributos no vacíos entre encuesta y reserva; tolerancia temporal de un segundo.

Estos controles forman parte del procesamiento de datos. `OK` en la conciliación estructural confirma filas y vínculos; no significa que todos los estados o valores sean correctos desde la perspectiva del negocio.

## Archivos de apoyo

- `controles_carga.csv`: conciliación por grupo y registros con banderas.
- `conciliacion_archivos.csv`: conteos para los 114 archivos/hojas.
- `diccionario_columnas.csv`: encabezado original → columna Silver.
- `diccionario_campos_adicionales.csv`: significado y tipos de trazabilidad e indicadores.
- `bitacora_transformaciones.csv`: celdas afectadas por regla.
- `mapa_programas.csv`: valores originales y normalizados.
- `casos_revision.csv` y `resumen_banderas.csv`: evidencia de revisión.
- `resumen_limpieza.json`: resumen de la ejecución.

## Leer y reproducir

Los CSV son UTF-8; una celda vacía representa nulo. CSV no conserva tipos: leer códigos e identificadores como texto, fechas según formato ISO 8601 y los indicadores true/false como booleanos nullable. Evitar que una librería convierta automáticamente respuestas como NA en nulos.

```sh
python3 src/limpiar_bookeau.py
```

El script regenera los cinco CSV y los controles principales a partir de Bronze. Los documentos narrativos y diccionarios de campos adicionales describen esta versión y deben revisarse al cambiar las reglas. Las tablas se escriben en un archivo temporal y se reemplazan cuando se completa cada escritura.

El cuaderno `notebooks/03_limpieza_bookeau.ipynb` consulta los controles y permite ejecutar nuevamente el proceso. Los agregados exploratorios previos en `docs/calidad/` proceden de Bronze. El modelo y los resultados actuales en `docs/analisis/resultados/` consumen Gold construido desde Silver, con conciliación y reglas R01/R02.

## Regla R01 incorporada

Aporte de María Alejandra Pérez compartido el 2 de octubre de 2026: Finalizada y Realizada se tratan igual para el análisis. Silver añade `estado_reserva_analitico = Atendida` para esos dos estados; conserva `estado_reserva`. La explicación sobre encuesta incompleta sigue siendo tentativa y no se utiliza para inferir validez o completitud. Ver [reglas_negocio.md](reglas_negocio.md).

## Regla R02 incorporada

Decisión del usuario: excluir encuestas Inválida de los análisis. Cada encuesta incluye `incluir_encuesta_en_analisis` y `motivo_exclusion_encuesta`; los conteos de calidad conservan las exclusiones. Hay 53 exclusiones en satisfacción Express, 111 en satisfacción Normal, 2 en la previa Normal IP y ninguna en la previa Express: 166 en total. Las reservas asociadas permanecen en demanda y atención.
