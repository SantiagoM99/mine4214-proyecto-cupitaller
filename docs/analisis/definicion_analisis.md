# Definición de los dos análisis · Entrega 1

Propuesta de análisis para el contexto CupiTaller / Bookeau, basada en el README del paquete y la caracterización de todos los Excel. Los roles destinatarios son propuestos; todavía no se ha confirmado el organigrama ni entrevistado al responsable de la fuente.

## Análisis 1. Patrones de reservas y atención registrada

**Objetivo:** identificar patrones del volumen de eventos de reserva y sus estados por período, modalidad, servicio, día y hora, para orientar la planificación de tutorías y la revisión del proceso de atención.

**Destinatario propuesto:** coordinación operativa de CupiTaller.

**Proceso de origen:** solicitudes de reserva y su evolución en Bookeau, exportadas por período con categorías, tipos de horario y servicios seleccionados como «Todos», según el README de la fuente.

**Datos:** 86.562 registros de Reservas, con 17 variables. Grano observado: una fila por ID de evento de reserva. Inicio y fin son programados; no hay fin efectivo registrado.

### Preguntas

1. ¿Cómo varía el número de eventos de reserva por período, servicio y modalidad?
2. ¿En qué días y horas programadas se concentra ese volumen?
3. ¿Cómo se distribuyen los estados registrados en cada segmento?
4. Una vez confirmados estados y población elegible: ¿qué proporción de los eventos elegibles se atiende, se cancela o termina sin asistencia?

### Indicadores y denominadores

| Indicador | Definición | Denominador / población | Estado actual |
|---|---|---|---|
| Eventos de reserva | `COUNT(DISTINCT ID)` en el segmento | Todos los eventos de la selección, incluidos espera y cancelaciones | Calculable; describir como eventos registrados |
| Distribución de estados | Eventos con cada etiqueta literal | Todos los eventos del mismo segmento | Calculable; no requiere agrupar estados |
| Agenda por día y hora | Eventos por día ISO y hora de `Fecha inicio` | Eventos de la selección con inicio disponible | Calculable; hora tal como se exportó, sin conversión de zona horaria |
| Minutos programados | Diferencia entre fin e inicio programados | Eventos con ambos campos temporales coherentes | Calculable; no representa atención efectiva |
| Tasa de asistencia | Eventos Finalizada o Realizada / eventos elegibles | Numerador agrupado según R01; población elegible por confirmar | Numerador definido como regla de trabajo; denominador pendiente |
| Tasa de inasistencia | Eventos elegibles clasificados como no asistidos / eventos elegibles | Definir tratamiento de espera, cancelaciones y estados abiertos | Pendiente de definición de negocio |
| Tasa de cancelación | Eventos clasificados como cancelados / población definida | Definir inclusión de cancelación de cola y cancelación por sanción | Pendiente de definición de negocio |

La población puede contener modalidades distintas a tutoría: entrevistas, salas y etiquetas históricas. Mostrarla segmentada. Para una comparación directa Express/Normal, usar las etiquetas exactas y documentar qué modalidades quedaron fuera; `Normal pico` permanece separada hasta justificar su equivalencia.

### Calidad necesaria

ID completo y único; fechas válidas; categorías conservadas y catálogo histórico documentado; clasificación de estados confirmada; revisión de excepciones estado–llegada. La falta de llegada no se convierte automáticamente en inasistencia. No se puede medir capacidad utilizada: no hay oferta completa de horarios ni capacidad disponible explícita.

## Análisis 2. Satisfacción y percepción de las tutorías

**Objetivo:** describir calificación y percepción de las tutorías por modalidad, período y servicio, para identificar segmentos que ameritan revisión de la experiencia de los estudiantes.

**Destinatario propuesto:** coordinación académica de CupiTaller.

**Proceso de origen:** encuestas posteriores a la tutoría. El README las describe como encuestas de satisfacción Express y Normal; no explica su obligatoriedad, la regla de invalidez ni los cambios históricos de formularios.

**Datos:** 6.759 registros en Encuesta Express (33 variables) y 16.379 en Encuesta Normal (35 variables), vinculados por ID a Reservas. Se usa la modalidad registrada en la reserva para segmentar, además del grupo de archivo.

### Preguntas

1. ¿Cómo se distribuyen las calificaciones 1–5 del tutor por período, servicio y modalidad?
2. ¿Cuál es la mediana y el promedio descriptivo de esas calificaciones, y cuántas respuestas sustentan cada resultado?
3. ¿Cómo se comparan Express y Normal dentro de períodos y servicios que tienen respuestas de ambas modalidades?
4. ¿Qué porcentaje de las respuestas de encuesta incluidas tiene una calificación utilizable?
5. ¿Qué percepciones y temas aparecen en las demás respuestas y comentarios? El análisis de texto se desarrollará en las siguientes entregas.

### Indicadores y denominadores

| Indicador | Definición | Denominador / población | Estado actual |
|---|---|---|---|
| Calificaciones utilizables | Respuestas marcadas `Válida` con calificación entera 1–5 | Encuestas marcadas Válida del segmento; regla R02 adoptada | Calculable como subconjunto descriptivo |
| Distribución 1–5 | Número de cada calificación / calificaciones utilizables | Calificaciones utilizables del mismo segmento | Calculable; mostrar conteos además de porcentajes |
| Mediana y media | Resumen de la calificación utilizable | Calificaciones utilizables; mostrar `n` y distribución | Media supone distancias equivalentes entre puntos; confirmar escala |
| Completitud del ítem | Calificaciones utilizables / respuestas marcadas `Válida` | Encuestas marcadas válidas del mismo segmento | Calculable; no equivale a tasa de respuesta a la encuesta |
| Tasa de respuesta de encuesta | Reservas elegibles con respuesta / reservas elegibles | Definir invitación, elegibilidad, estados y períodos del instrumento | Pendiente de definición de negocio |
| Comparación Express/Normal | Comparar dentro del mismo período y servicio original | Etiquetas exactas Express y Normal con calificación en ambas | Exploratoria; confirmar equivalencia del instrumento |

El filtrado por `Estado = Válida` es la regla R02 adoptada explícitamente por el usuario. Las respuestas Inválida se excluyen de numeradores y denominadores analíticos; se conservan y cuentan en auditoría. Su reserva sigue en los análisis de demanda y atención. No se imputan preguntas vacías con cero. La fecha de inicio de reserva ubica el evento en el tiempo; no demuestra cuándo se contestó la encuesta.

### Calidad necesaria

Vínculos completos y únicos; separación entre estado de reserva y estado de encuesta; calificación en dominio observado; disponibilidad por período; conciliación de atributos repetidos; conocimiento de escalas, formularios históricos y validez de respuestas.

El grupo de archivo no determina por sí solo la modalidad: Encuesta Express incluye 61 registros `Deprecated, Grupal`; Encuesta Normal incluye 1.461 `Normal pico` y 87 `Deprecated, Torre Séneca`. No comparar los totales de grupos como si fueran exclusivamente Express y Normal.

La falta de respuestas y la autoselección pueden afectar las comparaciones. Un resultado de satisfacción no demuestra mejora del aprendizaje ni que una modalidad cause mejores resultados.

## Reglas de trabajo adoptadas para esta etapa

- Conservar los nombres, valores originales y trazabilidad por ID y período.
- Usar ID para vincular encuestas a eventos de reserva; su unicidad se vuelve a comprobar al procesar.
- Usar los atributos de Reservas para segmentar las respuestas como referencia provisional explícita, y registrar diferencias con los atributos de encuesta. Esto no decide cuál es la verdad histórica.
- Mantener servicios históricos y modalidades separados; no asumir equivalencias por parecido del nombre.
- Agrupar Finalizada y Realizada como Atendida en un campo adicional, según la regla de trabajo R01 aportada por María Alejandra Pérez; conservar originales. La explicación sobre encuesta incompleta es tentativa y no se convierte en un indicador.
- Generar agregados descriptivos y evidencia de calidad; las reglas operativas pendientes permanecen identificadas.

## Fuentes y próximos pasos

Documentación local revisada: `docs/fuente_bookeau_README.md`, `docs/Proyecto - entrega 1.pdf` y `docs/caracterizacion/`.

La matriz de reglas y su evidencia está en `docs/calidad/evaluacion_para_analisis.md`. Con estas definiciones se puede proponer el modelo conceptual y avanzar en un borrador de ecosistema, dejando trazadas las reglas operativas pendientes.

## Aclaración recibida el 2 de octubre de 2026

La equivalencia analítica Finalizada/Realizada fue incorporada en Silver. Ver `docs/limpieza/reglas_negocio.md`. Todavía se requiere confirmar la población elegible, los otros estados y el criterio de encuesta inválida.

## Decisiones adoptadas

R01: Finalizada y Realizada → Atendida en un campo analítico. R02: excluir encuestas marcadas Inválida de indicadores y análisis de respuestas; mantenerlas en Silver con trazabilidad. Las reglas no identifican quién dejó una encuesta pendiente ni determinan el denominador de asistencia.

## Implementación del modelo y consumo

El modelo conceptual y la materialización Gold están en `docs/modelo/` y `data/oro/`. El tablero `entregables/tablero_bookeau.html` consume agregados calculados desde Gold. Los resultados actuales están en `docs/analisis/respuestas_analisis.md`. Se excluyen explícitamente preguntas de ocupación, cupos libres y demanda frente a capacidad por ausencia de oferta general.

## Replanteamiento para el informe (octubre de 2026)

Los dos análisis se reformularon en función de la decisión que apoyan (ver sección 1 del informe):

1. **Inasistencia y presión de cola.** Supuesto **D1** (del equipo, por validar con la coordinación): la cola no ocupa cupo. Tasa de inasistencia = No asistió / (Atendida + No asistió); proporción en cola = (En cola + Cola cancelada por reservación) / eventos. Los estados abiertos (En ejecución, Reservada) quedan fuera de la tasa.
2. **Satisfacción.** Indicador principal: proporción de calificaciones 1–3 sobre las calificadas, porque la escala tiene efecto techo (81,7% de cincos; mediana 5).

Consultas en `sql/01_consultas_analisis.sql`; implementación en `src/generar_tablero_bookeau.py`.
