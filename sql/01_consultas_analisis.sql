-- Ejecutar sobre data/oro/bookeau.sqlite3. Gold solo tiene reservas de tutorías (R03) y encuestas válidas (R02).
-- El período académico es un atributo de dim_fecha (se une por la fecha de inicio de la reserva).
-- Análisis 1: eventos registrados y atención R01, sin asumir capacidad disponible.
SELECT p.periodo_original, s.servicio_original, m.tipo_horario_original,
       COUNT(*) AS eventos_registrados,
       SUM(CASE WHEN e.estado_analitico='Atendida' THEN 1 ELSE 0 END) AS atenciones_registradas,
       SUM(CASE WHEN e.estado_original='No asistió' THEN 1 ELSE 0 END) AS inasistencias_registradas
FROM hecho_reserva h
JOIN dim_fecha p ON p.sk_fecha=h.sk_fecha_inicio
JOIN dim_servicio s USING(sk_servicio)
JOIN dim_modalidad m USING(sk_modalidad)
JOIN dim_estado e USING(sk_estado)
GROUP BY p.periodo_original,s.servicio_original,m.tipo_horario_original;

-- Análisis 2: calificación de encuestas posteriores incluidas, con denominador del ítem.
SELECT p.periodo_original, s.servicio_original, m.tipo_horario_original,
       COUNT(*) AS encuestas_posteriores_incluidas,
       COUNT(h.calificacion_ayuda_tutor) AS n_calificaciones,
       AVG(h.calificacion_ayuda_tutor) AS media_descriptiva,
       100.0*COUNT(h.calificacion_ayuda_tutor)/COUNT(*) AS completitud_item_pct
FROM hecho_encuesta h
JOIN dim_tipo_encuesta t USING(sk_tipo_encuesta)
JOIN dim_fecha p ON p.sk_fecha=h.sk_fecha_inicio
JOIN dim_servicio s USING(sk_servicio)
JOIN dim_modalidad m USING(sk_modalidad)
WHERE t.etapa='posterior'
GROUP BY p.periodo_original,s.servicio_original,m.tipo_horario_original;

-- Texto válido disponible para etapas futuras; no mezclar su grano con reservas.
SELECT q.texto_pregunta,t.grupo_fuente,COUNT(*) AS respuestas_textuales
FROM hecho_respuesta r
JOIN dim_pregunta q USING(sk_pregunta)
JOIN hecho_encuesta e USING(id_encuesta)
JOIN dim_tipo_encuesta t USING(sk_tipo_encuesta)
WHERE q.es_texto_libre=1
GROUP BY q.texto_pregunta,t.grupo_fuente;

-- Análisis 1 (R04): tasa de inasistencia y proporción en cola por modalidad.
-- dim_estado.grupo_estado materializa R04: inasistencia = No asistió / (Atendida + No asistió).
SELECT m.tipo_horario_original AS modalidad,
       COUNT(*) AS eventos,
       ROUND(100.0*SUM(e.grupo_estado='No asistió')
             /SUM(e.grupo_estado IN ('Atendida','No asistió')),1) AS inasistencia_pct,
       ROUND(100.0*SUM(e.grupo_estado='Cola')/COUNT(*),1) AS cola_pct
FROM hecho_reserva h
JOIN dim_modalidad m USING(sk_modalidad)
JOIN dim_estado e USING(sk_estado)
GROUP BY m.tipo_horario_original
ORDER BY eventos DESC;

-- Análisis 1 (R04): inasistencia por día de la semana y franja horaria (jerarquías de Fecha y Hora).
SELECT d.dia_semana_iso, d.nombre_dia, t.franja,
       SUM(e.grupo_estado IN ('Atendida','No asistió')) AS citas_programadas,
       ROUND(100.0*SUM(e.grupo_estado='No asistió')
             /SUM(e.grupo_estado IN ('Atendida','No asistió')),1) AS inasistencia_pct
FROM hecho_reserva h
JOIN dim_fecha d ON d.sk_fecha=h.sk_fecha_inicio
JOIN dim_hora t ON t.sk_hora=h.sk_hora_inicio
JOIN dim_estado e USING(sk_estado)
GROUP BY d.dia_semana_iso, d.nombre_dia, t.franja
ORDER BY d.dia_semana_iso, t.franja;

-- Análisis 1: eventos y cola por tipo de período (atributos de período en dim_fecha).
SELECT p.tipo_periodo, COUNT(*) AS eventos,
       ROUND(100.0*SUM(e.grupo_estado='Cola')/COUNT(*),1) AS cola_pct
FROM hecho_reserva h
JOIN dim_fecha p ON p.sk_fecha=h.sk_fecha_inicio
JOIN dim_estado e USING(sk_estado)
GROUP BY p.tipo_periodo;

-- Análisis 2: proporción de calificaciones 1–3 por período (encuestas posteriores válidas).
SELECT p.periodo_original,
       COUNT(h.calificacion_ayuda_tutor) AS n_calificaciones,
       ROUND(100.0*SUM(h.calificacion_ayuda_tutor<=3)/COUNT(h.calificacion_ayuda_tutor),1) AS bajas_pct
FROM hecho_encuesta h
JOIN dim_tipo_encuesta t USING(sk_tipo_encuesta)
JOIN dim_fecha p ON p.sk_fecha=h.sk_fecha_inicio
WHERE t.etapa='posterior'
GROUP BY p.periodo_original
HAVING COUNT(h.calificacion_ayuda_tutor)>=30;
