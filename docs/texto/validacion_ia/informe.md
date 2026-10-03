# Revisión del clasificador de comentarios

Fecha: 2026-10-02. Referencia: revisión semántica de Codex, no etiquetas humanas verificadas.

## Conclusión

**El clasificador de reglas todavía no es suficientemente fiable para evaluar o comparar monitores.** La versión corregida coincidió con la revisión IA en **62 de 100 comentarios de evaluación reservada**. Los otros 38 son desacuerdos respecto de esa referencia, que también puede contener errores.

Revisé y etiqueté 250 comentarios. Sus etiquetas y justificaciones están en `../etiquetas_revisadas_ia.csv`, identificadas como revisión IA. No completé el archivo de etiquetas humanas con estas respuestas. El tablero muestra por defecto comentarios revisados y permite incluir las reglas provisionales; retiré los porcentajes por monitor porque la muestra revisada no representa las opiniones de cada monitor.

## Procedimiento

1. Conservé las predicciones originales v1 antes de ajustar reglas.
2. Revisé 150 comentarios de desarrollo, 30 por categoría automática original. Leí una copia mezclada sin predicciones ni nombres de monitor visibles.
3. Ajusté reglas usando esa revisión: contexto de dificultades previas del estudiante, negaciones y vocabulario favorable/desfavorable. Este ajuste logró coincidencia en los 150 casos utilizados para desarrollarlo; **ese resultado no demuestra generalización**.
4. Congelé las predicciones v2 y seleccioné otros 100 comentarios, 20 por categoría v1, excluyendo textos normalizados vistos en desarrollo y repeticiones dentro de evaluación. Revisé esa copia sin mostrar las predicciones.
5. Comparé ambas versiones con la referencia IA. No volví a ajustar las reglas después de leer la evaluación reservada.

Las predicciones congeladas, las muestras, las semillas y los hashes de código están conservados en esta carpeta. El mismo asistente desarrolló las reglas y produjo la referencia: ocultar predicciones reduce su influencia inmediata, pero **no proporciona independencia entre desarrollador y evaluador**.

## Resultados

| Versión | Desarrollo, 150 comentarios | Evaluación reservada, 100 comentarios |
|---|---:|---:|
| v1 original | 88/150 (58.7%) | 57/100 (57%) |
| v2 corregida | 150/150 (100%) | 62/100 (62%) |

Resultados v2 por categoría, respecto de la revisión IA:

| Categoría | Referencias IA | Predicciones | Precisión respecto de IA | Recobrado respecto de IA | F1 |
|---|---:|---:|---:|---:|---:|
| Positivo | 46 | 31 | 80.6% | 54.3% | 0.649 |
| Negativo | 21 | 15 | 73.3% | 52.4% | 0.611 |
| Mixto | 13 | 16 | 43.8% | 53.8% | 0.483 |
| Sin información suficiente | 18 | 20 | 90.0% | 100% | 0.947 |
| Por revisar | 2 | 18 | 5.6% | 50.0% | 0.100 |

Macro F1 de las cinco categorías: 0.558. Precisión significa coincidencias de una categoría divididas por las predicciones de esa categoría; recobrado significa coincidencias divididas por las referencias IA de esa categoría. `Por revisar` es una abstención operativa, no una polaridad: su F1 se incluye para describir las cinco salidas, pero no debe interpretarse como valoración del monitor.

Estas cifras describen la muestra estratificada. **El 62% no es una estimación de exactitud sobre los 17,829 comentarios**, y los porcentajes de categorías de la muestra no estiman la prevalencia del corpus ni de cada monitor. No se evalúa aquí la exactitud de los temas léxicos ni la identidad de monitores.

## Errores observados

| Caso de evaluación | Predicción v2 | Revisión IA | Problema |
|---|---|---|---|
| Todo perfecto | Por revisar | Positivo | Falta de vocabulario favorable |
| El tutor fue un poco grosero y agresivo hacia mi persona | Por revisar | Negativo | `poco` suprime indebidamente una crítica |
| A pesar del poco tiempo fue capaz de aclararme dudas | Negativo | Positivo | La restricción temporal domina el beneficio expresado |
| Me permitió ver los errores que tenía y como corregirlos. | Por revisar | Positivo | No reconoce una valoración favorable implícita |

Otros desacuerdos mezclan elogios con problemas de conexión, sugerencias de mejora o críticas al trato. Algunos casos requieren decidir si el comentario critica al tutor, a la sesión o a una restricción externa. La revisión IA documenta su interpretación, sin convertirla en una verdad verificada.

## Uso en el proyecto

- Las 250 revisiones IA pueden utilizarse para explorar casos y desarrollar criterios, manteniendo su origen y justificación.
- Las 17,579 etiquetas sin revisión individual siguen siendo provisionales. No justifican un ranking ni tasas de desempeño por monitor.
- Una revisión humana futura tiene prioridad sobre IA; la revisión IA tiene prioridad sobre la regla para la etiqueta final. La predicción original queda conservada.
- Si se usa esta evaluación para desarrollar otra versión, deja de ser una evaluación reservada: será necesario otro conjunto de evaluación.
- Para mejorar se requiere un método que interprete contexto y una nueva evaluación separada. No basta con que las reglas memoricen estas dos muestras.

## Reproducción

```sh
python3 src/evaluar_clasificador_ia.py
python3 src/clasificar_comentarios_monitores.py
python3 src/generar_tablero_monitores.py
```

La evaluación compara predicciones congeladas, no etiquetas finales ya corregidas. `resultados.json` contiene matrices de confusión y métricas; `desacuerdos.csv` conserva texto, versiones y justificación. La reproducción de cálculos no sustituye una segunda anotación independiente.
