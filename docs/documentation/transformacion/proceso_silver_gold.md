# Proceso Silver → Gold

## Entradas y reglas

Se leen los cinco CSV Silver. De las reservas solo entran las de tutorías (R03: tipo de horario Normal, Express o Normal pico); las demás permanecen en Silver. Para encuestas se incluye exclusivamente `incluir_encuesta_en_analisis = true` según R02 y solo si su reserva está en Gold (R03); los falsos se excluyen de Gold analítico y permanecen en Silver. Un indicador desconocido requiere revisión y se concilia por separado.

R01 llega a `dim_estado` como etiqueta original y etiqueta analítica. No se infiere encuesta completa ni duración efectiva. Servicios y modalidades históricos se mantienen separados. La segmentación de encuesta usa la reserva vinculada; las discrepancias del origen se mantienen como auditoría, sin afirmar que se reconstruyó la verdad histórica.

## Secuencia de transformación

1. Comprobar unicidad de reservas y respuestas de cada grupo y coincidencia del período de la encuesta con la reserva.
2. Generar el calendario diario continuo para el rango de inicio, fin y llegada observados, y los 1.440 minutos del día.
3. Asignar a cada día del calendario su período académico (el de las reservas que empiezan ese día; los días sin reservas toman el período que los rodea o «Entre períodos») y construir catálogos distintos de servicio, modalidad/categoría, estado y programa, sin equivalencias históricas inventadas. El período es un atributo de `dim_fecha`: no hay dimensión de período.
4. Construir tipo de encuesta y preguntas, manteniendo el texto íntegro del encabezado y reutilizando preguntas de igual texto entre fuentes.
5. Cargar un hecho por reserva, con fechas reales de la extracción, duración programada y trazabilidad.
6. Cargar un hecho por encuesta incluida; copiar las claves de segmentación de su reserva.
7. Cargar un hecho de respuesta para cada pregunta no vacía de esa encuesta. Conservar textos y categorías; asignar valor numérico solo a la calificación 1–5, sin mapear escalas Likert a números arbitrariamente.
8. Aplicar restricciones SQL, comprobar claves foráneas y conciliar los conteos antes de publicar la base local.

## Resultados y mecanismo aplicado

La carga produce 86.562 reservas, 60.224 encuestas incluidas y 384.792 respuestas no vacías. Las 166 encuestas inválidas quedan fuera de Gold y dentro de Silver. Las encuestas con campos de respuesta vacíos se conservan a su grano de encuesta, pero no generan respuestas inventadas.

`conciliacion_silver_gold.csv` contiene conteos por fuente. `controles_gold.json` registra filas por tabla, atención R01 y resultado de integridad. Las claves primarias, únicas, CHECK y foráneas se aplicaron al insertar en SQLite; los conteos de hechos se reconciliaron con Silver. No se encontraron referencias huérfanas ni granos duplicados.

No se exige igualdad entre el conteo de respuestas y el de encuestas: sus granos son distintos. No sumar una medida de reserva después de unirla directamente con múltiples encuestas o preguntas. Para comparar hechos, agregar primero por dimensiones conformadas.

## Correcciones que corresponden al origen

Confirmar diferencias técnicas de estados, criterios de invalidez, llegada en estados contradictorios, catálogo Deprecated, etiquetas de programas y versiones de preguntas. La oferta disponible y fecha efectiva de salida requieren captura adicional: no se corrigen imputándolas en ETL. Una exportación con identidad de pregunta y versión del formulario permitiría comprobar comparabilidad histórica mejor que el encabezado actual.

## Reproducción

```sh
python3 src/construir_gold_bookeau.py
```

Se reconstruye el modelo desde Silver usando Python y SQLite estándar. La base temporal sustituye la versión anterior solo cuando termina la carga y se completan sus controles. Los CSV y documentos describen esta extracción; al cambiar reglas se deben revisar también las definiciones analíticas. El proceso no publica datos fuera del equipo local.
