# Reglas de negocio de limpieza y clasificación

## R01 · Equivalencia analítica de Finalizada y Realizada

**Origen:** conversación de María Alejandra Pérez compartida por el usuario el 2 de octubre de 2026, 09:37–09:38. No es una definición oficial de Bookeau.

**Aporte recibido:** María Alejandra indica que trata Finalizada y Realizada igual, y señala como posible diferencia que el estudiante o tutor no completó la encuesta. También indica que no ha podido determinar el detalle de Bookeau.

**Regla de trabajo adoptada:** en el campo adicional `estado_reserva_analitico`, mapear ambos estados a `Atendida`. En `estado_reserva`, conservar siempre la etiqueta original. Los demás estados conservan su etiqueta sin una reclasificación adicional.

**Alcance:** equivalencia para el análisis de atención registrada. No certifica duración efectiva, existencia de marca de llegada ni encuesta completada. Las banderas de calidad se conservan, incluidos los casos Finalizada sin llegada.

**Limitaciones de la explicación sobre encuestas:** el mensaje no especifica cuál de los dos estados corresponde a una encuesta pendiente, quién debía completarla ni la relación con el estado Inválida. No derivar esos atributos automáticamente. Las fuentes compartidas son encuestas de estudiantes; no hay una fuente separada identificada de respuestas de tutores.

**Denominador pendiente:** la agrupación define un conjunto de atención registrada, pero no fija la población elegible para una tasa de asistencia. No usar todos los eventos —incluida cola, entrevistas y salas— como denominador sin justificarlo.

**Implementación:** `src/limpiar_bookeau.py`; auditoría de aplicación en `bitacora_transformaciones.csv`, regla `regla_R01_finalizada_realizada_a_atendida`.

La regla debe revisarse si se recibe documentación oficial o una aclaración adicional del responsable del proceso.

## Comprobación de encuestas sobre Silver

La comprobación por ID muestra encuesta posterior exportada en el 55,80% de Finalizada (21.507/38.541) y el 39,46% de Realizada (1.620/4.105). Ambos estados incluyen eventos con y sin encuesta. Por tanto, no se confirma una relación determinista entre estado y encuesta completada, y tampoco se puede comprobar la encuesta de tutor con estas fuentes. R01 se conserva como regla analítica de atención, sin inferir completitud o validez. Evidencia: `docs/calidad/estados_encuestas/comprobacion.md`.

## R02 · Excluir encuestas marcadas Inválida de los análisis

**Origen:** decisión explícita del usuario el 2 de octubre de 2026, después del cruce de estados y encuestas.

**Regla adoptada:** las encuestas marcadas `Inválida` no participan en indicadores de satisfacción, análisis de respuestas previas ni análisis de texto. Se conservan en Silver para auditoría, con `incluir_encuesta_en_analisis = false` y motivo `estado_origen_invalida_R02`. Las marcadas `Válida` tienen el indicador true. Un estado desconocido deja el indicador vacío y requiere revisión.

**Denominadores:** excluir respuestas Inválida tanto de numeradores como de denominadores de indicadores basados en encuestas. Mantenerlas en conteos de calidad y de cobertura de la extracción, identificados como tales. La exclusión de una encuesta no elimina su reserva ni altera los conteos de demanda o atención. Para indicadores de cobertura de respuestas utilizables, usar solo las encuestas incluidas y confirmar aparte la población de reservas elegibles.

**Alcance:** la decisión acepta la etiqueta de validez exportada como criterio operativo del proyecto. No demuestra que una encuesta esté completa ni explica el mecanismo interno de Bookeau. La regla se aplica a las cuatro fuentes de encuesta.

**Implementación:** `src/limpiar_bookeau.py`, campos adicionales de inclusión y motivo; auditoría de aplicación en `bitacora_transformaciones.csv`. Los resúmenes de calificación preparados previamente ya usaban solo la etiqueta Válida, por lo que su criterio coincide con esta decisión. Sus estadísticas continúan siendo exploratorias por las limitaciones de cobertura y de instrumentos históricos.
