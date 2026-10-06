# Diccionario inicial de variables

Los nombres se conservan como vienen de Bookeau. Los significados operativos se infieren de los encabezados y del README de la fuente, salvo los vínculos de ID verificados. Confirmar captura, escalas y reglas con el responsable de CupiTaller.

El detalle completo está en `diccionario_variables.csv`; tipos, nulos y cardinalidad están en `variables.csv`. Los períodos de primera y última respuesta no prueban cuándo se creó una pregunta: pueden reflejar cambios del formulario, de etiquetas o del exportador.

## Variables comunes

| Variable | Descripción inicial |
| --- | --- |
| ID | Identificador del evento de reserva. Único en cada grupo; todas las encuestas lo comparten con Reservas. |
| Fecha inicio | Inicio programado del evento, interpretado a partir del encabezado y del formato Excel. |
| Fecha fin | Fin programado del evento. No equivale a una salida real registrada. |
| Fecha de llegada | Marca temporal de llegada según el encabezado; confirmar procedimiento de captura y excepciones. |
| Fecha de devolución | Campo temporal sin valores en todos los archivos; su significado operativo debe confirmarse. |
| Estado de la reserva | Estado del evento de reserva, con 12 etiquetas en la fuente principal. No confundir con Estado de la encuesta. |
| Prioritaria | Indicador sí/no de prioridad de la reserva; confirmar regla de asignación. |
| Categoría | Categoría de recurso o prestación, como Tutor Presencial; incluye identificadores históricos Deprecated. |
| Tipo de horario | Modalidad o tipo de agenda: Normal, Express, Normal pico y otras modalidades históricas. |
| Servicio | Servicio o curso asociado: IP, EDA y etiquetas históricas, entre otros. |
| Código servicio | Código de servicio en Reservas; corresponde al campo Código del servicio en encuestas. |
| Código del servicio | Código de servicio en encuestas; homologar el nombre con Código servicio sin modificar el original. |
| Usuario | Nombre del usuario que reserva; no utilizar como clave única de persona. |
| Correo usuario | Correo del usuario; conservar como atributo, sujeto a validación de identidad. |
| Código usuario | Identificador de usuario exportado como texto. Sus 9.943 valores distintos en Reservas no demuestran 9.943 estudiantes únicos. |
| Tipo de usuario | Clasificación del usuario en Bookeau; no corresponde al programa académico. |
| Programa | Programa reportado para el usuario. Presenta variantes de escritura; no equivale a una lista homologada de programas. |
| Prestador del servicio | Prestador o tutor asociado según el encabezado. Frecuentemente vacío en eventos sin atención; confirmar lógica de asignación. |
| Estado | Estado de validez de la respuesta de encuesta: Válida o Inválida. No es el estado de asistencia. |

## Encuesta Express

| Pregunta / variable | Tipo inicial | No vacíos | % faltantes | Primer período con valores |
| --- | --- | --- | --- | --- |
| ¿El tiempo fue adecuado para resolver su problema o duda puntual? | categoría o respuesta | 6759 | 0.0 | 201710 |
| La mayor parte del tiempo de la tutoría lo dediqué a | categoría o respuesta | 3529 | 47.7881 | 201920 |
| Califique la ayuda que le dio su tutor | categoría o respuesta | 4983 | 26.2761 | 201819 |
| El tutor me explicó cómo solucionar mi duda/problema/proyecto | categoría o respuesta | 4983 | 26.2761 | 201819 |
| El tutor aclaró y reforzó conceptos | categoría o respuesta | 4983 | 26.2761 | 201819 |
| El tutor me brindó herramientas adicionales para trabajar por mi cuenta | categoría o respuesta | 4983 | 26.2761 | 201819 |
| El tutor fue receptivo frente a mis inquietudes durante la tutoría | categoría o respuesta | 5448 | 19.3964 | 201810 |
| El tutor es capaz de expresar claramente su conocimiento sobre el tema o temas trabajados | categoría o respuesta | 6263 | 7.3384 | 201710 |
| Durante la tutoría, el tutor hizo uso de alguna herramienta de inteligencia artificial, tal como pero no limitándose a ChatGPT, Bard/Gemini o Bing AI. | categoría o respuesta | 2703 | 60.0089 | 202210 |
| Indique cuál fue la herramienta usada durante la tutoría (si sabe cuál es) y el uso que tuvo la misma en la tutoría. | texto libre | 4 | 99.9408 | 202520 |
| ¿Cuál considera que es su comprensión del tema actual del curso? | categoría o respuesta | 1910 | 71.7414 | 202210 |
| ¿Considera que el material del curso permite un buen proceso de aprendizaje? | categoría o respuesta | 1910 | 71.7414 | 202210 |
| Comente aspectos positivos y negativos del tutor y la tutoría. Recuerde que las respuestas van a ser anónimas. | texto libre | 5453 | 19.3224 | 201720 |
| Escriba en este recuadro cualquier observación o comentario relacionado al curso y sus contenidos. | texto libre | 564 | 91.6556 | 202320 |
| Sugerencias, reclamos y observaciones | texto libre | 1730 | 74.4045 | 201710 |

## Encuesta Normal

| Pregunta / variable | Tipo inicial | No vacíos | % faltantes | Primer período con valores |
| --- | --- | --- | --- | --- |
| La tutoría a la que asistí me permitió entender que la solución de un problema usando herramientas de programación es un proceso que implica leer el problema, entender los requerimientos, planear un algoritmo, escribir el código y probar lo implementado | categoría o respuesta | 16347 | 0.1954 | 201620 |
| La tutoría a la que asistí se enfocó en el desarrollo de mis habilidades de análisis y no solo en la corrección de mi código | categoría o respuesta | 16359 | 0.1221 | 201620 |
| La mayor parte del tiempo de la tutoría lo dediqué a | categoría o respuesta | 16366 | 0.0794 | 201620 |
| Aproveché el tiempo de la tutoría haciendo preguntas puntuales al tutor y participando de manera proactiva en el desarrollo de las mismas | categoría o respuesta | 16364 | 0.0916 | 201620 |
| Califique la ayuda que le dio su tutor | categoría o respuesta | 11326 | 30.8505 | 201819 |
| El tutor me explicó cómo solucionar mi duda/problema/proyecto | categoría o respuesta | 11326 | 30.8505 | 201819 |
| El tutor aclaró y reforzó conceptos | categoría o respuesta | 11326 | 30.8505 | 201819 |
| El tutor me brindó herramientas adicionales para trabajar por mi cuenta | categoría o respuesta | 16355 | 0.1465 | 201620 |
| El tutor fue receptivo frente a mis inquietudes durante la tutoría | categoría o respuesta | 16360 | 0.116 | 201620 |
| El tutor es capaz de expresar claramente su conocimiento sobre el tema o temas trabajados | categoría o respuesta | 16366 | 0.0794 | 201620 |
| Durante la tutoría, el tutor hizo uso de alguna herramienta de inteligencia artificial, tal como pero no limitándose a ChatGPT, Bard/Gemini o Bing AI. | categoría o respuesta | 6074 | 62.9159 | 202120 |
| Indique cuál fue la herramienta usada durante la tutoría (si sabe cuál es) y el uso que tuvo la misma en la tutoría. | texto libre | 22 | 99.8657 | 202510 |
| ¿Cuál considera que es su comprensión del tema actual del curso? | categoría o respuesta | 4442 | 72.8799 | 202120 |
| ¿Considera que el material del curso permite un buen proceso de aprendizaje? | categoría o respuesta | 4442 | 72.8799 | 202120 |
| Comente aspectos positivos y negativos del tutor y la tutoría. Recuerde que las respuestas van a ser anónimas. | texto libre | 12534 | 23.4752 | 201720 |
| Escriba en este recuadro cualquier observación o comentario relacionado al curso y sus contenidos. | texto libre | 1329 | 91.886 | 202120 |
| Sugerencias, reclamos y observaciones | texto libre | 4053 | 75.2549 | 201620 |

## Encuesta Reserva Express

| Pregunta / variable | Tipo inicial | No vacíos | % faltantes | Primer período con valores |
| --- | --- | --- | --- | --- |
| La mayoría del tiempo de la tutoría que estoy reservando lo usaré para | categoría o respuesta | 13815 | 0.0 | 201920 |
| Entiendo que durante la tutoría no debo usar mi celular | categoría o respuesta | 13815 | 0.0 | 201920 |
| Acepto que si quiero trabajar en una tarea en senecode debo tener una solución probada y que pueda explicar, en caso de no cumplir estas condiciones se configurará un comportamiento inadecuado | categoría o respuesta | 13815 | 0.0 | 201920 |
| Acepto que he leído los términos de uso de CupiTaller que están disponibles en la URL https://cupitaller.uniandes.edu.co/terminos-de-uso/ | categoría o respuesta | 13815 | 0.0 | 201920 |

## Encuesta Reserva Normal IP

| Pregunta / variable | Tipo inicial | No vacíos | % faltantes | Primer período con valores |
| --- | --- | --- | --- | --- |
| La mayoría del tiempo de la tutoría que estoy reservando lo usaré para | categoría o respuesta | 23437 | 0.0 | 201920 |
| Entiendo que durante la tutoría no debo usar mi celular | categoría o respuesta | 23437 | 0.0 | 201920 |
| Acepto que si quiero trabajar en una tarea en senecode debo tener una solución probada y que pueda explicar, en caso de no cumplir estas condiciones se configurará un comportamiento inadecuado | categoría o respuesta | 23437 | 0.0 | 201920 |
| Acepto que he leído los términos de uso de CupiTaller que están disponibles en la URL https://cupitaller.uniandes.edu.co/terminos-de-uso/ | categoría o respuesta | 23437 | 0.0 | 201920 |

