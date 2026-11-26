# Requisitos y plan · Entrega 1

Fuente: `Proyecto - entrega 1.pdf`, MINE-4214, septiembre de 2026.

## Productos solicitados

| Punto | Valor | Producto y criterios |
|---|---:|---|
| 1. Objetivo y análisis | 5 | Describir organización y dependencia. Definir al menos dos análisis con objetivo, rol destinatario, datos y proceso de origen. Caracterizar cantidad de datos y variables. |
| 2. Ecosistema de analítica | 5 | Graficar y describir el ecosistema existente o propuesto, justificarlo e identificar componentes que se intervendrán. |
| 3. Exploración y calidad | 8 | Estadísticas y evaluación de completitud, unicidad, consistencia y validez. Para faltantes: ubicación, cantidad y porcentaje. Revisar duplicados totales y semánticos, coherencia entre variables, formatos y sentido de los valores. |
| 4. Modelo conceptual | 12 | Proponer modelos dimensionales según los procesos de los análisis. Describir y justificar; definir criterios de calidad del modelo y su suficiencia. |
| 5. Transformación Silver → Gold | 12 | Diseñar la adecuación a la estructura propuesta, justificar decisiones y señalar correcciones que corresponden a la fuente. Definir y aplicar un mecanismo para validar las transformaciones. |
| 6. Respuesta a los análisis | 8 | Uno o más tableros, y criterios que demuestran que el modelo es adecuado para los análisis. |
| 7. Gestión del proyecto | Sin puntaje explícito | Describir contribuciones y distribuir 100 puntos entre integrantes con justificación; identificar problemas y estrategias. Documentar uso de IA generativa, ventajas y riesgos para la organización. |

## Restricciones

- Datos tabulares y otros formatos, como textos; los textos se utilizarán en las siguientes entregas.
- Entre 80.000 y 200.000 registros esperados. Contrastar el inventario con este rango y definir la unidad de registro; evitar contabilizar reservas repetidas entre fuentes como eventos nuevos.
- Equipo de 3 a 4 estudiantes. Integrantes pendientes de confirmar; no se trasladan automáticamente los de Taller 1.
- Evaluación grupal: 75%; individual: 25%, utilizando la respuesta al punto 7.
- El enunciado compartido no especifica una fecha de entrega ni exige una plataforma concreta.

## Avance

- [x] Crear el espacio de trabajo siguiendo Taller 1.
- [x] Incorporar el PDF y conservar el ZIP original de Bookeau.
- [x] Extraer las fuentes manteniendo la estructura y los nombres originales.
- [x] Leer el enunciado y registrar los requisitos.
- [x] Generar inventario por archivo, hoja, período y encabezados.
- [ ] Confirmar integrantes, contexto organizacional y roles destinatarios.
- [x] Definir dos análisis con objetivos, roles propuestos, medidas, preguntas y denominadores.
- [x] Preparar evidencia de calidad y agregados descriptivos para esos análisis.
- [x] Ejecutar limpieza inicial Bronze → Silver con trazabilidad, banderas y conciliación.
- [ ] Revisar casos marcados y completar reglas operativas de limpieza.
- [x] Hacer que los análisis consuman Gold construido desde Silver y conciliar sus resultados.
- [x] Realizar caracterización inicial completa, perfilamiento y verificación de ID y vínculos.
- [ ] Confirmar reglas operativas, catálogos y formularios históricos con la fuente para completar la evaluación de calidad.
- [x] Proponer y justificar el ecosistema de analítica.
- [x] Diseñar grano, hechos, dimensiones y criterios de calidad del modelo.
- [x] Diseñar y ejecutar transformaciones Silver → Gold con conciliación de resultados.
- [x] Generar tablero local y documentar respuestas iniciales.
- [x] Revisar visualmente el tablero (capturas en `img/`).
- [x] Supuesto D1 confirmado por la coordinación: ahora es la regla R04.
- [ ] Validar con la coordinación la interpretación de resultados.
- [ ] Volver a ejecutar Gold, tablero y cifras del informe con la regla R03 (solo reservas de tutorías).
- [x] Informe autocontenido con tablas, diagramas y capturas; PDF en `entregables/`.
- [x] Ejecutar los cuadernos.
- [ ] Completar integrantes, contribuciones y distribución de 100 puntos, y revisión final.

## Análisis seleccionados para desarrollar

1. **Patrones de reservas y atención registrada:** estudiar reservas y estados por período, tipo de tutoría y servicio, orientado a la coordinación de CupiTaller. Confirmar el significado de estados y fechas antes de calcular indicadores.
2. **Satisfacción de estudiantes:** estudiar respuestas a encuestas por tipo de tutoría y período, orientado a la coordinación académica. Revisar escalas, cobertura de respuestas y posibles vínculos con reservas antes de comparar resultados.

Las preguntas, indicadores y denominadores están en `analisis/definicion_analisis.md`. La evaluación específica de calidad está en `calidad/evaluacion_para_analisis.md`. Los roles son propuestos y las tasas operativas siguen pendientes de reglas de negocio confirmadas.

## Evidencia de caracterización

La caracterización inicial y el diccionario están en `caracterizacion/`. Se identificaron 86.562 ID de reserva únicos y vínculo completo de las cuatro encuestas. Las limitaciones observadas y las reglas pendientes están documentadas en `caracterizacion/caracterizacion_bookeau.md`.

## Limpieza inicial

Reglas y resultados en `limpieza/README.md`. Se generaron cinco CSV Silver conservando todos los registros. La normalización de programas se incorpora en una columna adicional; los estados y las respuestas cuestionadas permanecen con banderas para revisión.

## Regla de negocio recibida

R01: agrupar Finalizada y Realizada como Atendida, con estado original conservado. Aporte de María Alejandra Pérez compartido el 2 de octubre de 2026; explicación de encuesta incompleta pendiente de detalle. Regla aplicada a Silver y documentada en `limpieza/reglas_negocio.md`.

## Comprobación de la explicación sobre encuestas

Se cruzaron por ID los estados originales con las encuestas previas/posteriores y se compararon estratos comunes. Hay registros con y sin encuesta posterior en ambos estados; la explicación de María Alejandra no se confirma como regla determinista con esta extracción. Ver `calidad/estados_encuestas/comprobacion.md`.

## Decisión de exclusión de encuestas

R02 adoptada: excluir encuestas Inválida de los análisis y mantenerlas en Silver para auditoría. Se añade indicador de inclusión y motivo de exclusión; las reservas no se eliminan.

## Modelo y consumo implementados

Ecosistema propuesto en `arquitectura/`; diagrama E/R y modelo dimensional en `modelo/`. Gold: 86.562 reservas, 60.224 encuestas incluidas y 384.792 respuestas no vacías, conciliadas con Silver. Tablero local y borrador del informe en `entregables/`. Los datos de oferta/capacidad no están disponibles; se documenta esa limitación y no se publican indicadores de ocupación.

## Exploración textual por monitor

Se añadió un clasificador exploratorio basado en reglas y un tablero por etiqueta de monitor, manteniendo R02. Corpus: 17.829 comentarios, de los que 295 quedan sin monitor confirmado. Muestra humana sin completar; revisión IA de 250 textos realizada. Coincidencia v2 en evaluación reservada: 62/100, insuficiente para evaluar monitores. Ver docs/texto/validacion_ia/informe.md. Es una extensión acordada con el usuario, no un requisito adicional de la primera entrega.
