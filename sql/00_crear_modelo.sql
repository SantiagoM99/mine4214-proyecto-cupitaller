PRAGMA foreign_keys = ON;
CREATE TABLE dim_fecha(sk_fecha INTEGER PRIMARY KEY, fecha TEXT UNIQUE NOT NULL, anio INTEGER, mes INTEGER, dia INTEGER, dia_semana_iso INTEGER CHECK(dia_semana_iso BETWEEN 1 AND 7), nombre_dia TEXT NOT NULL, nombre_mes TEXT NOT NULL, es_fin_de_semana INTEGER CHECK(es_fin_de_semana IN (0,1)));
CREATE TABLE dim_hora(sk_hora INTEGER PRIMARY KEY, hora INTEGER, minuto INTEGER, etiqueta TEXT, franja TEXT NOT NULL CHECK(franja IN ('Madrugada','Mañana','Tarde','Noche')));
CREATE TABLE dim_periodo(sk_periodo INTEGER PRIMARY KEY, periodo_original TEXT UNIQUE NOT NULL, anio_codigo INTEGER, sufijo_original TEXT, tipo_periodo TEXT NOT NULL);
CREATE TABLE dim_servicio(sk_servicio INTEGER PRIMARY KEY, codigo_servicio TEXT, servicio_original TEXT, UNIQUE(codigo_servicio, servicio_original));
CREATE TABLE dim_modalidad(sk_modalidad INTEGER PRIMARY KEY, tipo_horario_original TEXT, categoria_original TEXT, UNIQUE(tipo_horario_original,categoria_original));
CREATE TABLE dim_estado(sk_estado INTEGER PRIMARY KEY, estado_original TEXT UNIQUE NOT NULL, estado_analitico TEXT NOT NULL, grupo_estado TEXT NOT NULL CHECK(grupo_estado IN ('Atendida','No asistió','Cola','Cancelada','Abierta')));
CREATE TABLE dim_programa(sk_programa INTEGER PRIMARY KEY, programa_normalizado TEXT UNIQUE NOT NULL);
CREATE TABLE dim_tipo_encuesta(sk_tipo_encuesta INTEGER PRIMARY KEY, grupo_fuente TEXT UNIQUE NOT NULL, etapa TEXT NOT NULL);
CREATE TABLE dim_pregunta(sk_pregunta INTEGER PRIMARY KEY, columna_plata TEXT UNIQUE NOT NULL, texto_pregunta TEXT NOT NULL, es_texto_libre INTEGER CHECK(es_texto_libre IN (0,1)), es_calificacion_tutor INTEGER CHECK(es_calificacion_tutor IN (0,1)));
CREATE TABLE hecho_reserva(
 id_reserva TEXT PRIMARY KEY, sk_fecha_inicio INTEGER REFERENCES dim_fecha, sk_fecha_fin INTEGER REFERENCES dim_fecha,
 sk_fecha_llegada INTEGER REFERENCES dim_fecha, sk_hora_inicio INTEGER NOT NULL REFERENCES dim_hora,
 sk_periodo INTEGER NOT NULL REFERENCES dim_periodo, sk_servicio INTEGER NOT NULL REFERENCES dim_servicio,
 sk_modalidad INTEGER NOT NULL REFERENCES dim_modalidad, sk_estado INTEGER NOT NULL REFERENCES dim_estado,
 sk_programa INTEGER NOT NULL REFERENCES dim_programa,
 fecha_inicio TEXT NOT NULL, fecha_fin TEXT NOT NULL, fecha_llegada TEXT,
 duracion_programada_minutos REAL CHECK(duracion_programada_minutos>=0), es_prioritaria INTEGER CHECK(es_prioritaria IN (0,1)),
 evento_reserva INTEGER NOT NULL DEFAULT 1 CHECK(evento_reserva=1),
 archivo_origen TEXT NOT NULL, hoja_origen TEXT NOT NULL, fila_excel INTEGER NOT NULL, banderas_calidad_json TEXT NOT NULL);
CREATE TABLE hecho_encuesta(
 id_encuesta TEXT PRIMARY KEY, id_reserva TEXT NOT NULL REFERENCES hecho_reserva,
 sk_tipo_encuesta INTEGER NOT NULL REFERENCES dim_tipo_encuesta,
 sk_fecha_inicio INTEGER REFERENCES dim_fecha, sk_hora_inicio INTEGER NOT NULL REFERENCES dim_hora,
 sk_periodo INTEGER NOT NULL REFERENCES dim_periodo, sk_servicio INTEGER NOT NULL REFERENCES dim_servicio,
 sk_modalidad INTEGER NOT NULL REFERENCES dim_modalidad, sk_estado INTEGER NOT NULL REFERENCES dim_estado,
 sk_programa INTEGER NOT NULL REFERENCES dim_programa,
 calificacion_ayuda_tutor INTEGER CHECK(calificacion_ayuda_tutor BETWEEN 1 AND 5),
 respuesta_encuesta INTEGER NOT NULL DEFAULT 1 CHECK(respuesta_encuesta=1),
 archivo_origen TEXT NOT NULL, hoja_origen TEXT NOT NULL, fila_excel INTEGER NOT NULL,
 banderas_calidad_json TEXT NOT NULL, diferencias_con_reserva_json TEXT NOT NULL,
 UNIQUE(id_reserva,sk_tipo_encuesta));
CREATE TABLE hecho_respuesta(
 id_encuesta TEXT NOT NULL REFERENCES hecho_encuesta,
 sk_pregunta INTEGER NOT NULL REFERENCES dim_pregunta,
 valor_original TEXT NOT NULL CHECK(length(trim(valor_original))>0),
 valor_numerico REAL, respuesta_item INTEGER NOT NULL DEFAULT 1 CHECK(respuesta_item=1),
 PRIMARY KEY(id_encuesta,sk_pregunta));
