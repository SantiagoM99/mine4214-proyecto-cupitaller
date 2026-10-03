# Calidad de datos para los dos análisis

## Documentación consultada

Se revisó íntegramente `docs/fuente_bookeau_README.md`. Explica fuentes, propósito de encuestas, duración nominal de 30 minutos/1 hora y exportación, pero **no define** Finalizada frente a Realizada, criterios de encuesta Inválida, equivalencias Deprecated ni calendario de cambios del cuestionario. Esas reglas no se deducen como hechos únicamente de las etiquetas.

## Matriz de evaluación

| Dimensión / regla | Resultado observado | Tratamiento actual | Implicación |
|---|---|---|---|
| Unicidad de ID | 86.562 ID de reserva únicos; ID único en cada encuesta | Comprobar de nuevo antes de unir | Grano y uniones disponibles |
| Integridad de vínculos | 100% de encuestas vincula por ID y período | Conservar ID y período | Segmentación común disponible |
| Completitud temporal | Inicio/fin completos; devolución 100% vacía | Distinguir horario programado de atención real | Duración efectiva no disponible |
| Consistencia de fechas | Sin fin anterior al inicio ni inicio fuera del año del período | Mantener evidencia; revisar reglas operativas adicionales | Agenda programada disponible |
| Consistencia estado–llegada | 49 casos para revisión | Conservar y señalar; no corregir automáticamente | No usar llegada como única regla de asistencia |
| Consistencia entre fuentes | Diferencias en estado, identidad, programa y prestador | Segmentación con Reservas como referencia provisional; mantener evidencia | Acordar conciliación y momento de actualización |
| Estandarización | Variantes de programa; servicios y modalidades Deprecated | Guardar originales y candidatos de homologación | No colapsar categorías históricas sin catálogo |
| Dominio de calificación | Respuestas no vacías observadas dentro de 1–5 | Separar faltantes; no imputar cero | Resumen descriptivo disponible |
| Validez de encuesta | 53 Express y 111 Normal marcadas Inválida | Contar todos los estados; subconjunto Válida según regla R02 adoptada | Confirmar criterio de la fuente |
| Cobertura temporal de preguntas | Respuestas disponibles en períodos diferentes | Calcular cobertura por pregunta/período | No asumir equivalencia del formulario histórico |
| Tipo de horario | Los grupos de encuesta contienen otras modalidades | Segmentar por atributo de la reserva, conservando grupo de encuesta | Evitar comparación incorrecta de grupos enteros |

## Excepciones de estado y llegada

| Caso para revisar | Registros |
|---|---:|
| Estado de cancelación con marca de llegada | 32 |
| Finalizada sin marca de llegada | 8 |
| No asistió con marca de llegada | 9 |

No son errores confirmados ni registros descartados. `casos_revision_estado_llegada.csv` conserva ID y período para revisión. `catalogo_estados_pendiente.csv` presenta los 12 estados y su evidencia de llegada conservando las etiquetas originales. La regla R01 ahora agrupa Finalizada y Realizada como Atendida en Silver; las demás clasificaciones siguen pendientes.

## Elegibilidad de la calificación según R02

Estas cifras usan el estado de validez exportado, sin asegurar que la regla de invalidez del sistema sea conocida. Los grupos siguen siendo grupos de fuente y pueden incluir distintas modalidades.

| Grupo de fuente | Respuestas | Marcadas Válida | Otro estado | Calificación 1–5 en Válida | Falta calificación en Válida | Fuera de dominio en Válida |
|---|---:|---:|---:|---:|---:|---:|
| Encuesta Express | 6759 | 6706 | 53 | 4938 | 1768 | 0 |
| Encuesta Normal | 16379 | 16268 | 111 | 11233 | 5035 | 0 |

Se identificaron **37 combinaciones de período y servicio original** con calificaciones en ambas modalidades exactas Express y Normal, después del filtrado por validez ahora adoptado como R02. Se conservan `n`, completitud y medias descriptivas en `estratos_comunes_express_normal.csv`. La coincidencia de pregunta, período y servicio es necesaria para comparar, pero no demuestra equivalencia de formularios ni elimina sesgos.

## Resultados preparados

| Archivo | Contenido |
|---|---|
| `demanda_por_periodo_modalidad_servicio_estado.csv` | Conteos de eventos con categorías originales; incluye todos los estados |
| `agenda_por_dia_hora.csv` | Distribución del inicio programado por día ISO y hora exportada |
| `satisfaccion_por_periodo_modalidad_servicio.csv` | Conteos, estados de validez, faltantes, distribución 1–5 y resúmenes provisionales |
| `estratos_comunes_express_normal.csv` | Estratos con ambas modalidades exactas y denominadores visibles |
| `resumen_elegibilidad_satisfaccion.csv` | Conciliación entre respuestas exportadas, válidas y con calificación |
| `casos_revision_estado_llegada.csv` | Evidencia por ID de casos que requieren aclaración |
| `catalogo_estados_pendiente.csv` | Etiquetas originales, conteos y reglas pendientes |

## Reglas que requieren confirmación de la fuente

1. Confirmar oficialmente la diferencia técnica entre Finalizada y Realizada y completar la clasificación de los otros estados. Su equivalencia analítica se adopta como regla de trabajo R01 aportada por María Alejandra Pérez.
2. Población elegible para tasas de asistencia y cancelación, tratamiento de la cola y momento de captura de llegada.
3. Criterio de encuesta Inválida, población invitada y si la encuesta es obligatoria.
4. Catálogos históricos de servicios/modalidades, significado de períodos y zona horaria de las marcas temporales.
5. Cuestionarios y escalas por período; si la exportación utiliza etiquetas actuales para respuestas históricas.
6. Fuente de referencia y momento de actualización para atributos de reserva repetidos en encuestas.

Mientras se confirman estas reglas, pueden presentarse volumen de eventos, agenda programada, distribuciones de etiquetas y calificaciones del subconjunto documentado. Las tasas definitivas de asistencia y respuesta de encuesta aún no están definidas.

## Reproducción

```sh
python3 src/preparar_analisis_bookeau.py
```

El script vuelve a leer los 114 Excel, comprueba claves antes de unir y genera los CSV y `resumen_preparacion.json`. No modifica las fuentes originales ni publica tasas operativas no definidas. El documento narrativo describe esta extracción y debe revisarse si cambian los datos o las reglas.

## Actualización de regla de negocio

María Alejandra Pérez indicó que trata Finalizada y Realizada de manera equivalente, con una posible diferencia de encuesta incompleta. Se aplica la agrupación Atendida en Silver, conservando estados originales y banderas. No se infiere qué encuesta quedó pendiente ni el significado de Inválida. Ver `docs/limpieza/reglas_negocio.md`.

## Decisión de exclusión R02

El usuario confirmó la exclusión analítica de encuestas marcadas Inválida. La regla queda aplicada en Silver mediante `incluir_encuesta_en_analisis`; los conteos de calidad siguen incluyendo esas filas. Se excluyen de indicadores y análisis de texto, sin eliminar sus reservas.
