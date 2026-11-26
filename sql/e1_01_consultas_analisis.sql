-- Ejecutar sobre data/oro/bookeau.sqlite3. Gold solo tiene reservas de tutorías (R03) y encuestas válidas (R02).
-- Oferta: hecho_oferta (horarios por período, día y hora) cubre solo la categoría Tutor Presencial (R05).
-- Análisis 1: eventos registrados y atención R01, sin asumir capacidad disponible.
SELECT p.periodo_original, s.servicio_original, m.tipo_horario_original,
       COUNT(*) AS eventos_registrados,
       SUM(CASE WHEN e.estado_analitico='Atendida' THEN 1 ELSE 0 END) AS atenciones_registradas,
       SUM(CASE WHEN e.estado_analitico='No asistió' THEN 1 ELSE 0 END) AS inasistencias_registradas
FROM hecho_reserva h
JOIN dim_periodo p USING(sk_periodo)
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
JOIN dim_periodo p USING(sk_periodo)
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
       ROUND(100.0*SUM(e.grupo_estado='Cola')/COUNT(*),1) AS cola_pct,
       ROUND(100.0*SUM(e.grupo_estado='Cola a reserva')/COUNT(*),1) AS cola_a_reserva_pct
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

-- Análisis 1: eventos y cola por tipo de período (dim_periodo).
SELECT p.tipo_periodo, COUNT(*) AS eventos,
       ROUND(100.0*SUM(e.grupo_estado='Cola')/COUNT(*),1) AS cola_pct
FROM hecho_reserva h
JOIN dim_periodo p USING(sk_periodo)
JOIN dim_estado e USING(sk_estado)
GROUP BY p.tipo_periodo;

-- Análisis 2: proporción de calificaciones 1–3 por período (encuestas posteriores válidas).
SELECT p.periodo_original,
       COUNT(h.calificacion_ayuda_tutor) AS n_calificaciones,
       ROUND(100.0*SUM(h.calificacion_ayuda_tutor<=3)/COUNT(h.calificacion_ayuda_tutor),1) AS bajas_pct
FROM hecho_encuesta h
JOIN dim_tipo_encuesta t USING(sk_tipo_encuesta)
JOIN dim_periodo p USING(sk_periodo)
WHERE t.etapa='posterior'
GROUP BY p.periodo_original
HAVING COUNT(h.calificacion_ayuda_tutor)>=30;

-- Oferta: ocupación y lista de espera por franja y período.
-- Cupos disponibles es la capacidad total de la franja en el semestre (confirmado por la coordinación) y los
-- cupos reservados son los ya tomados: ocupación = reservados / disponibles. Se excluyen los períodos sin cupos
-- reservados registrados (201620 y 201710). En 5 franjas los reservados superan por poco a los disponibles.
SELECT p.periodo_original, d.nombre_dia, t.etiqueta AS hora, o.cupos_reservados, o.cupos_disponibles AS capacidad,
       ROUND(100.0*o.cupos_reservados/o.cupos_disponibles,1) AS ocupacion_pct,
       o.en_lista_espera, o.reservaron_luego_de_lista
FROM hecho_oferta o
JOIN dim_periodo p USING(sk_periodo)
JOIN dim_dia_semana d USING(sk_dia_semana)
JOIN dim_hora t ON t.sk_hora=o.sk_hora_inicio
WHERE o.cupos_disponibles>0
  AND o.sk_periodo IN (SELECT sk_periodo FROM hecho_oferta GROUP BY sk_periodo HAVING SUM(cupos_reservados)>0);

-- Oferta frente a demanda por período: capacidad, ocupación, lista de espera y conversión de la cola a reserva.
SELECT p.periodo_original, SUM(o.cupos_disponibles) AS capacidad,
       CASE WHEN SUM(o.cupos_reservados)>0
            THEN ROUND(100.0*SUM(o.cupos_reservados)/SUM(o.cupos_disponibles),1) END AS ocupacion_pct,
       SUM(o.asistencias) AS asistencias, SUM(o.en_lista_espera) AS en_lista_espera,
       SUM(o.reservaron_luego_de_lista) AS cola_a_reserva,
       ROUND(100.0*SUM(o.reservaron_luego_de_lista)/NULLIF(SUM(o.en_lista_espera+o.reservaron_luego_de_lista),0),1) AS conversion_cola_pct
FROM hecho_oferta o
JOIN dim_periodo p USING(sk_periodo)
GROUP BY p.periodo_original;

-- Cupos que se pierden por inasistencia frente a la lista de espera: en cuántas franjas las inasistencias
-- habrían alcanzado para atender a todos los que esperaban (comparación agregada, sin casar fechas).
SELECT p.periodo_original, SUM(o.inasistencias) AS inasistencias, SUM(o.en_lista_espera) AS en_lista_espera,
       SUM(o.en_lista_espera>0) AS franjas_con_lista,
       SUM(o.en_lista_espera>0 AND o.inasistencias>=o.en_lista_espera) AS franjas_donde_inasistencias_cubren_la_lista
FROM hecho_oferta o
JOIN dim_periodo p USING(sk_periodo)
GROUP BY p.periodo_original;

-- Análisis 2 (exploratorio): calificación según la saturación de la franja (tercil de ocupación).
-- Une la encuesta posterior con su franja (período, día de la semana y hora de inicio), solo Tutor Presencial.
WITH franja AS (
  SELECT o.sk_periodo, o.sk_dia_semana, o.sk_hora_inicio,
         NTILE(3) OVER (ORDER BY 1.0*o.cupos_reservados/o.cupos_disponibles) AS tercil_ocupacion
  FROM hecho_oferta o
  WHERE o.cupos_disponibles>0
    AND o.sk_periodo IN (SELECT sk_periodo FROM hecho_oferta GROUP BY sk_periodo HAVING SUM(cupos_reservados)>0))
SELECT f.tercil_ocupacion, COUNT(h.calificacion_ayuda_tutor) AS n_calificaciones,
       ROUND(AVG(h.calificacion_ayuda_tutor),2) AS media,
       ROUND(100.0*SUM(h.calificacion_ayuda_tutor<=3)/COUNT(h.calificacion_ayuda_tutor),1) AS bajas_pct
FROM hecho_encuesta h
JOIN dim_tipo_encuesta t USING(sk_tipo_encuesta)
JOIN dim_modalidad m USING(sk_modalidad)
JOIN dim_fecha d ON d.sk_fecha=h.sk_fecha_inicio
JOIN franja f ON f.sk_periodo=h.sk_periodo AND f.sk_dia_semana=d.dia_semana_iso AND f.sk_hora_inicio=h.sk_hora_inicio
WHERE t.etapa='posterior' AND m.categoria_original='Tutor Presencial'
GROUP BY f.tercil_ocupacion;
