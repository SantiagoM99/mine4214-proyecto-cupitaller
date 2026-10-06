# Comentarios por monitor · Exploración y clasificación

## Objetivo y estado

Explorar qué aspectos se valoran o cuestionan en los comentarios sobre tutor y tutoría y cómo se distribuyen por monitor, período, servicio y modalidad. Se utiliza exclusivamente la pregunta que pide aspectos positivos y negativos del tutor y tutoría; los comentarios generales del curso no se atribuyen al monitor.

**La versión corregida de reglas no es suficientemente fiable para evaluar monitores.** Coincidió con una revisión IA en 62 de 100 comentarios de evaluación reservada. Se revisaron 250 textos con justificación, manteniendo el origen IA separado de cualquier revisión humana. El mismo asistente desarrolló y revisó: esto no es validación humana independiente ni una estimación de exactitud poblacional. Véase [informe de evaluación](validacion_ia/informe.md).

## Fuentes e identificación

Hay **17,829 comentarios con contenido exportado** de encuestas posteriores incluidas por R02. De ellos, 17,534 coinciden en etiqueta de prestador entre encuesta y reserva tras normalizar mayúsculas/minúsculas, Unicode NFC y espacios, incluidos espacios no separables.

Se obtienen **424 etiquetas de monitor** con comentarios atribuidos. Son etiquetas normalizadas, no 424 identidades personales certificadas. No se eliminan tildes para unir nombres ni se fusionan personas mediante similitud aproximada.

Los **295 comentarios sin monitor confirmado** se mantienen aparte: 291 tienen nombres diferentes entre las fuentes y 4 no tienen monitor en ninguna. No se asignan a una persona hasta resolver la diferencia. R01 mantiene atención agrupada, pero no resuelve identidad del prestador ni confirma quién contestó una encuesta de tutor.

La pregunta habla de anonimato de las respuestas, pero el paquete permite vincular ID y prestador. Este análisis utiliza esa vinculación local; no declara que el archivo de origen sea anónimo ni publica el tablero.

## Categorías y evidencia

| Categoría | Interpretación de la regla |
|---|---|
| Positivo | Hay señales favorables reconocidas y ninguna desfavorable reconocida |
| Negativo | Hay señales desfavorables reconocidas y ninguna favorable reconocida |
| Mixto | Se reconocen señales de ambos tipos en el comentario |
| Sin información suficiente | Solo símbolos o respuestas genéricas como nada, ninguno o N/A |
| Por revisar | Texto con contenido pero sin señal reconocida por las reglas |

Cada registro conserva el texto original, reglas positivas/negativas activadas, etiqueta automática, etiqueta final, origen de la etiqueta y temas. Las negaciones se revisan en una ventana corta y se limita el contexto por signos de puntuación. Eso no resuelve ironía, errores de escritura, negaciones complejas o sentido del discurso; los casos pueden corregirse manualmente.

## Distribución automática actual (v2)

| Etiqueta | Comentarios |
|---|---:|
| Por revisar | 2,273 |
| Positivo | 12,299 |
| Sin información suficiente | 2,569 |
| Negativo | 327 |
| Mixto | 361 |

Estos conteos describen predicciones provisionales. Las 250 revisiones IA sobrescriben la etiqueta final del registro correspondiente, manteniendo su predicción automática y justificación. Una corrección humana tiene prioridad sobre ambas. Las 17,579 restantes carecen de revisión individual.

## Tablero por monitor

Abrir `exploratorio/tablero_monitores.html`. Permite filtrar monitor, período, servicio, modalidad y clasificación; buscar dentro del comentario; consultar temas; leer los textos y la evidencia de reglas; y corregir etiquetas durante la sesión.

El tablero muestra por defecto los comentarios revisados por IA o personas. El selector de alcance permite incluir todas las reglas provisionales. El resumen por monitor se ordena alfabéticamente y expone conteos; se retiraron porcentajes porque la muestra revisada es estratificada y no representa la distribución de opiniones de cada monitor. Estos conteos tampoco permiten comparar desempeño.

Los filtros de clasificación y búsqueda afectan la lista de comentarios y los temas; el resumen mantiene los filtros de alcance, monitor, período, servicio y modalidad.

Temas detectados: claridad, resolución de dudas, trato, tiempo, conocimiento, puntualidad, aprendizaje y conectividad/modalidad. Son menciones léxicas y pueden solaparse. Mencionar tiempo o duda no implica un problema; una etiqueta negativa del comentario tampoco demuestra que todos sus temas sean negativos.

## Revisión y evaluación humana

Se creó `docs/texto/etiquetas_manuales.csv` con una muestra de 150 comentarios, 30 de cada categoría automática, seleccionados con semilla fija. Las etiquetas humanas están vacías. Es una muestra estratificada para revisar comportamiento y criterios, no una muestra representativa de prevalencias.

Completar etiqueta_manual y observacion_revisor, preferiblemente con dos revisores que discutan desacuerdos. Mantener Positivo, Negativo, Mixto, Sin información suficiente o Por revisar. La anotación humana puede sobrescribir la etiqueta final, conservando la automática.

Al regenerar, el script compara etiquetas automáticas con humanas y publica una matriz de confusión sobre los registros revisados. La coincidencia de esa muestra no equivale a precisión poblacional ni a evaluación independiente; para evaluar un clasificador entrenado posteriormente hará falta separar datos de desarrollo y evaluación y considerar el desequilibrio de clases.

El tablero también permite correcciones y descarga de etiquetas. Los cambios en navegador no escriben los archivos del proyecto. Para persistirlos, guardar el CSV descargado como etiquetas_manuales.csv y regenerar. La descarga reemplaza el conjunto de anotaciones si se usa ese archivo; no combina por sí sola revisiones externas.

## Artefactos y reproducción

- `data/oro/texto/comentarios_clasificados.csv`: corpus, identidad, etiquetas, evidencias y contexto.
- `data/oro/texto/monitores.csv`: etiquetas de monitor y claves derivadas.
- `data/oro/texto/resumen_monitores_segmentos.csv`: conteos por segmento.
- `data/oro/texto/temas_monitores.csv`: temas mencionados.
- `docs/texto/etiquetas_manuales.csv`: muestra inicial o anotaciones conservadas.
- `docs/texto/etiquetas_revisadas_ia.csv`: 250 referencias IA con justificación y partición de desarrollo/evaluación.
- `docs/texto/validacion_ia/informe.md`: procedimiento, limitaciones, resultados y errores.
- `docs/texto/evaluacion_clasificador.json`: estado real de evaluación y matriz cuando hay revisión.
- `docs/texto/resumen.json`: conteos y cobertura.
- `exploratorio/tablero_monitores.html`: explorador local con revisión.

```sh
python3 src/evaluar_clasificador_ia.py
python3 src/clasificar_comentarios_monitores.py
python3 src/generar_tablero_monitores.py
```

Es una extensión exploratoria de los dos análisis de esta entrega; el enunciado reserva el uso de texto para las siguientes. El núcleo dimensional no cambia: el corpus parte de hecho_respuesta y encuesta Gold, y obtiene la etiqueta de prestador de Silver. Los scripts se ejecutaron sobre la extracción actual; la inspección visual completa en navegador y la validación humana quedan pendientes. Se comprobaron los cálculos de la evaluación y la ejecución del tablero en un DOM simulado; esto no sustituye inspección visual.
