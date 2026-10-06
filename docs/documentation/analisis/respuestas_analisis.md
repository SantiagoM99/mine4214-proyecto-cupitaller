# Respuestas iniciales a los análisis · Gold

## Alcance

Resultados de los 86.562 eventos exportados, de agosto de 2016 a mayo de 2026. Los totales incluyen modalidades históricas, salas y entrevistas; el tablero permite separarlas. No son totales de horarios ofrecidos, personas únicas ni atención efectiva medida por duración.

## 1. Patrones de reservas y atención registrada

- Se registran **86.562 eventos**, de los que **42.646** tienen Finalizada o Realizada y se agrupan como Atendida según R01.
- La etiqueta No asistió corresponde a **5.086** eventos. Los otros estados conservan su detalle; no se agrupan todos como no atendidos.
- Los servicios con más eventos son IP (**53.272**), Deprecated, APO 1 (**21.136**) y EDA (**6.127**), manteniendo sus etiquetas originales.
- Las modalidades con más eventos son Normal (**49.472**), Express (**25.754**) y Normal pico (**8.668**), que se mantiene separada.
- Las horas de inicio programado con más eventos, agregando todo el rango, son 11:00–11:59 (**13.699**), 14:00–14:59 (**11.253**) y 09:00–09:59 (**10.217**). Estos conteos reflejan agenda reservada y no demuestran insuficiencia de oferta.

La respuesta a variación por período y segmento se explora mediante los filtros del tablero y `resultados/reservas.csv` y `agenda.csv`. Una comparación temporal debe mantener el mismo servicio y modalidad; las etiquetas Deprecated no se homologan automáticamente con IP.

## 2. Satisfacción de estudiantes

Se incluyen **22.974 encuestas posteriores** tras R02. **16.171** tienen calificación 1–5; la completitud del ítem entre encuestas incluidas es **70.39%**. Faltan 6.803 calificaciones; no se les asigna cero. La media descriptiva global es **4.74/5** y la mediana es **5**.

| Modalidad original | Encuestas incluidas | Con calificación | Media descriptiva |
|---|---:|---:|---:|
| Express | 6.646 | 4.878 | 4,6982 |
| Normal | 14.731 | 9.722 | 4,7725 |
| Normal pico | 1.450 | 1.450 | 4,6241 |
| Deprecated, Grupal | 60 | 60 | 4,6000 |
| Deprecated, Torre Séneca | 87 | 61 | 4,7049 |

Las medias agregadas no demuestran superioridad de una modalidad. Se requiere comparar período, servicio, muestra y formulario; la media asume distancias equivalentes entre puntos de la escala. La ausencia de respuestas y los cambios históricos pueden sesgar la comparación. No se infiere una mejora causal en aprendizaje.

El tablero muestra el denominador de encuestas incluidas, el número de calificaciones, la distribución 1–5 y la completitud del ítem. No presenta la completitud como tasa de respuesta entre estudiantes invitados.

## Adecuación del modelo y del tablero

Los hechos tienen granos separados. El tablero consulta el hecho de reserva y el de encuesta por dimensiones conformadas sin unir filas de preguntas a reservas; evita multiplicación de conteos. Las preguntas largas y textos se conservan en el hecho de respuestas para las siguientes entregas.

La segmentación usa la reserva vinculada y conserva originales históricos. Los filtros aplican a ambos análisis y los casos sin registros se muestran explícitamente. Los agregados del tablero contienen solo información de grupos, sin nombres ni correos.

## Limitaciones pendientes

No hay oferta/capacidad general, fin efectivo, respuestas del tutor identificadas como fuente separada ni versiones certificadas del cuestionario. No están definidos todos los denominadores de tasas operativas. No se reconstruyen oportunidades de reserva que no se exportaron.

## Entregable y reproducción

Abrir `entregables/tablero_bookeau.html` en un navegador; funciona sin servidor ni conexión externa. Fue generado desde SQLite Gold. La inspección visual en navegador queda pendiente; se ejecutaron las consultas y controles de datos durante la construcción.

```sh
python3 src/construir_gold_bookeau.py
python3 src/generar_tablero_bookeau.py
```

Las consultas reproducibles están en `sql/01_consultas_analisis.sql`; los resultados CSV y el resumen están en `docs/analisis/resultados/`.
