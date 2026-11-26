-- Capa de consulta de la bodega para el agente. Son vistas sobre el modelo dimensional
-- Gold de la Entrega 1 (sql/bodega_modelo_gold.sql): resuelven los joins con las
-- dimensiones y dejan nombres de columna que se explican solos, para que el modelo
-- escriba SQL correcto sin conocer las llaves sustitutas.

DROP VIEW IF EXISTS v_reservas;
CREATE VIEW v_reservas AS
WITH inicio AS (
    -- Lunes de la semana de la primera reserva del período. Bookeau no guarda el
    -- calendario académico, así que la semana se cuenta desde ahí y es aproximada:
    -- las reservas abren una o dos semanas después del inicio de clases.
    SELECT sk_periodo, date(min(fecha_inicio), 'weekday 0', '-6 days') AS lunes_primera_semana
    FROM hecho_reserva
    GROUP BY sk_periodo
)
SELECT h.id_reserva,
       date(h.fecha_inicio)                AS fecha,
       p.periodo_original                  AS periodo,
       p.anio_codigo                       AS anio,
       p.tipo_periodo,
       CAST((julianday(date(h.fecha_inicio)) - julianday(i.lunes_primera_semana)) / 7 AS INTEGER) + 1
                                           AS semana_del_periodo,
       f.nombre_dia                        AS dia_semana,
       t.etiqueta                          AS hora,
       t.franja,
       s.servicio_original                 AS servicio,
       m.tipo_horario_original             AS tipo_tutoria,
       m.categoria_original                AS categoria_tutor,
       e.estado_original,
       e.grupo_estado                      AS estado,
       h.duracion_programada_minutos       AS duracion_minutos,
       h.es_prioritaria
FROM hecho_reserva h
JOIN inicio i        ON i.sk_periodo = h.sk_periodo
JOIN dim_periodo p   ON p.sk_periodo = h.sk_periodo
JOIN dim_fecha f     ON f.sk_fecha = h.sk_fecha_inicio
JOIN dim_hora t      ON t.sk_hora = h.sk_hora_inicio
JOIN dim_servicio s  ON s.sk_servicio = h.sk_servicio
JOIN dim_modalidad m ON m.sk_modalidad = h.sk_modalidad
JOIN dim_estado e    ON e.sk_estado = h.sk_estado;

DROP VIEW IF EXISTS v_encuestas;
CREATE VIEW v_encuestas AS
SELECT h.id_encuesta,
       h.id_reserva,
       p.periodo_original       AS periodo,
       p.anio_codigo            AS anio,
       te.etapa,
       s.servicio_original      AS servicio,
       m.tipo_horario_original  AS tipo_tutoria,
       h.calificacion_ayuda_tutor AS calificacion_tutor
FROM hecho_encuesta h
JOIN dim_tipo_encuesta te ON te.sk_tipo_encuesta = h.sk_tipo_encuesta
JOIN dim_periodo p        ON p.sk_periodo = h.sk_periodo
JOIN dim_servicio s       ON s.sk_servicio = h.sk_servicio
JOIN dim_modalidad m      ON m.sk_modalidad = h.sk_modalidad;

DROP VIEW IF EXISTS v_respuestas;
CREATE VIEW v_respuestas AS
SELECT r.id_encuesta,
       p.periodo_original  AS periodo,
       p.anio_codigo       AS anio,
       te.etapa,
       q.texto_pregunta    AS pregunta,
       r.valor_original    AS respuesta,
       r.valor_numerico
FROM hecho_respuesta r
JOIN dim_pregunta q       ON q.sk_pregunta = r.sk_pregunta
JOIN hecho_encuesta h     ON h.id_encuesta = r.id_encuesta
JOIN dim_tipo_encuesta te ON te.sk_tipo_encuesta = h.sk_tipo_encuesta
JOIN dim_periodo p        ON p.sk_periodo = h.sk_periodo;

-- Capacidad y ocupación por franja (período × día × hora), del reporte de horarios de
-- Bookeau cargado en hecho_oferta. Queda vacía si el Gold se construyó sin los archivos
-- de horarios. 201620 y 201710 no registran cupos reservados: su ocupación queda vacía.
DROP VIEW IF EXISTS v_oferta_franja;
CREATE VIEW v_oferta_franja AS
SELECT p.periodo_original           AS periodo,
       d.dia_semana_iso,
       d.nombre_dia                 AS dia_semana,
       t.etiqueta                   AS hora,
       o.cupos_disponibles          AS capacidad_cupos,
       o.cupos_reservados,
       CASE WHEN o.cupos_disponibles > 0 AND sin_registro.sk_periodo IS NULL
            THEN ROUND(100.0 * o.cupos_reservados / o.cupos_disponibles, 1) END AS ocupacion_pct,
       o.asistencias, o.cancelaciones, o.inasistencias, o.en_lista_espera, o.reservaron_luego_de_lista
FROM hecho_oferta o
JOIN dim_periodo p    ON p.sk_periodo = o.sk_periodo
JOIN dim_dia_semana d ON d.sk_dia_semana = o.sk_dia_semana
JOIN dim_hora t       ON t.sk_hora = o.sk_hora_inicio
LEFT JOIN (SELECT sk_periodo FROM hecho_oferta GROUP BY sk_periodo HAVING SUM(cupos_reservados) = 0) sin_registro
       ON sin_registro.sk_periodo = o.sk_periodo;
