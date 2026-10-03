# Comprobación de estados de reserva y encuestas

## Conclusión

**La extracción no confirma que Finalizada/Realizada identifique si una encuesta fue completada.** Hay reservas con y sin encuesta posterior exportada en ambos estados. Finalizada presenta mayor cobertura agregada, pero no determina la presencia ni la completitud de la encuesta. No hay una fuente separada identificada de encuestas de tutores, por lo que esa parte de la explicación no es comprobable con el paquete compartido.

Se mantiene R01 como equivalencia analítica de atención registrada aportada por María Alejandra Pérez; no se añade ninguna regla que deduzca encuesta pendiente, completada o inválida a partir del estado de reserva.

## Cruce por ID con el estado de Reservas

| Estado original | Eventos | Con encuesta posterior exportada | Sin encuesta posterior exportada | % con encuesta posterior |
|---|---:|---:|---:|---:|
| Finalizada | 38,541 | 21,507 | 17,034 | 55.80% |
| Realizada | 4,105 | 1,620 | 2,485 | 39.46% |

Los porcentajes usan como denominador todos los eventos de cada estado, con todas las modalidades y períodos. Son cobertura en los archivos compartidos, **no tasas de respuesta entre personas invitadas**. Una encuesta no exportada podría no haber sido requerida, existir fuera del paquete o no haber sido respondida; esta extracción no permite distinguir esos casos.

## Validez y presencia de respuestas

| Encuesta | Estado de reserva | Registros de encuesta | Marcados Inválida | Sin respuesta a ninguna pregunta exportada | Con calificación no vacía |
|---|---|---:|---:|---:|---:|
| Encuesta Express | Finalizada | 6299 | 51 | 0 | 4525 |
| Encuesta Express | Realizada | 457 | 2 | 0 | 455 |
| Encuesta Normal | Finalizada | 15208 | 107 | 12 | 10164 |
| Encuesta Normal | Realizada | 1163 | 1 | 0 | 1156 |

Las etiquetas de invalidez aparecen en ambos estados de reserva. En satisfacción Normal hay 12 registros asociados a Finalizada sin ninguna respuesta no vacía en las preguntas exportadas. Deben revisarse como casos de cobertura/contenido; no se concluye que sean errores ni se descartan. Una fila de encuesta y el estado Válida no garantizan que todas las preguntas exportadas tengan respuesta.

El conteo de preguntas con respuesta considera solo los campos de preguntas, no los atributos de reserva repetidos en la encuesta. “Todas las preguntas no vacías” no es un criterio de encuesta completa: hay preguntas opcionales, condicionales e históricas cuya obligatoriedad no conocemos.

## Comparación dentro de período, modalidad y servicio

Se encontraron 103 estratos con ambos estados. En 55 la proporción con encuesta posterior exportada es mayor en Finalizada; en 3 es mayor en Realizada y en 45 es igual. Los tamaños de cada estrato son distintos y algunos no tienen encuestas para ninguno de los dos estados. Estos conteos no son una prueba estadística ni una estimación ajustada.

Entre modalidades exactas Express y Normal hay 78 estratos con ambos estados. El detalle por estrato conserva denominadores y diferencias en puntos porcentuales, para evitar atribuir al estado una diferencia que podría depender de la época, servicio o modalidad.

La coincidencia de estrato tampoco controla formularios históricos, invitaciones ni encuestas del tutor. La asociación observada puede ser compatible con la explicación de encuesta pendiente en algunos casos, pero no establece una regla determinista del sistema.

## Método

- Fuente: cinco CSV Silver generados desde los 114 Excel.
- Estado principal: etiqueta original de la fuente Reservas; no se utiliza el campo agrupado Atendida para esta comprobación.
- Vínculo: ID completo y único por fuente; se comprueban existencia de reserva y unicidad de respuesta en cada grupo.
- Posterior: unión de IDs de satisfacción Express y Normal; previa: unión de los dos grupos de encuesta de reserva. No hay IDs compartidos entre las dos encuestas posteriores ni entre las dos previas.
- Las diferencias entre el estado repetido en la encuesta y el estado de Reservas se guardan separadamente. Por eso algunos conteos difieren de los calculados usando la etiqueta de la propia encuesta.
- No se elimina ninguna fila ni se asigna completitud a partir de Finalizada/Realizada.

## Archivos

- `resumen_por_estado.csv`: cobertura previa y posterior para todos los estados.
- `validez_completitud_por_estado.csv`: validez, respuestas presentes y calificación por grupo y estado.
- `cobertura_por_periodo_estado.csv`: cobertura por período.
- `cobertura_por_periodo_modalidad_servicio_estado.csv`: conteos con segmentación completa.
- `comparacion_estratos_comunes.csv`: comparación entre estados en el mismo período, modalidad y servicio.
- `estados_reserva_vs_encuesta.csv`: diferencias de estado entre las fuentes.
- `resumen.json`: resumen de ejecución.
- `casos_encuesta_sin_respuestas.csv`: trazabilidad de registros sin ninguna respuesta a preguntas exportadas.

## Reproducción y pendiente

```sh
python3 src/comprobar_estados_encuestas.py
```

El script regenera las tablas y el resumen. El documento narrativo describe esta extracción y debe revisarse si cambian las fuentes. Para confirmar la regla técnica se requiere documentación de Bookeau o del responsable del proceso que especifique la transición entre estados, la encuesta exigida y quién debe responderla.
