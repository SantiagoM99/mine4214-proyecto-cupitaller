"""Bodega de datos (Gold de la Entrega 1) preparada para que la consulte el agente.

    python3 src/bodega.py [--gold RUTA] [--silver-reservas RUTA]

Copia el SQLite Gold, le quita lo que no debe salir hacia un modelo externo, añade
las tablas agregadas que el Gold no trae (tipos de horario descontinuados, demanda por
franja y oferta por semestre) y crea las vistas de consulta. El Gold original no se
modifica.
"""

import argparse
import csv
import shutil
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

from config import BODEGA, OFERTA_POR_PERIODO, RAIZ

# La Entrega 2 vive en entrega2/ dentro del repositorio de la Entrega 1.
PROYECTO_1 = RAIZ.parent
GRUPOS_DE_ESTADO = {'Atendida', 'No asistió', 'Cola', 'Cola a reserva', 'Cancelada'}
MAX_FILAS = 200
MAX_INSTRUCCIONES_SQLITE = 50_000_000

# R05 de la Entrega 1: el reporte de horarios de Bookeau cubre solo esta categoría, y sus
# conteos por franja son exactamente estas sumas de estados de Reservas (verificado en
# 1.386 de 1.396 franjas; las otras 10 son de 202619, que no está en Reservas).
CATEGORIA_DE_LOS_HORARIOS = 'Tutor Presencial'
MEDIDA_DE_LA_FRANJA = {
    'Finalizada': 'asistencias', 'Realizada': 'asistencias', 'En ejecución': 'asistencias',
    'No asistió': 'inasistencias',
    'En cola': 'en_lista_espera',
    'Cola cancelada por reservación': 'reservaron_luego_de_lista',
}
MEDIDAS_DE_LA_FRANJA = ('asistencias', 'cancelaciones', 'inasistencias', 'en_lista_espera', 'reservaron_luego_de_lista')
DIAS = {1: 'lunes', 2: 'martes', 3: 'miércoles', 4: 'jueves', 5: 'viernes', 6: 'sábado', 7: 'domingo'}

# `dim_programa` conserva valores sucios de la fuente, entre ellos nombres de personas
# escritos en el campo de programa, y ninguna vista la usa.
TABLAS_VEDADAS = {'dim_programa'}

DESCRIPCION = """Bodega de CupiTaller (SQLite). Reservas de tutoría y encuestas de 2016-20 a 2026-10.
Los períodos se escriben sin guion: '202610' es 2026-10; el sufijo 10 es primer semestre, 20 segundo y 19 intersemestral.

v_reservas — una fila por reserva de tutoría (tipos Normal, Express y Normal pico).
  id_reserva, fecha (AAAA-MM-DD), periodo, anio, tipo_periodo ('Semestre 1' | 'Semestre 2' | 'Intersemestral'),
  semana_del_periodo (1 = semana de la primera reserva del período; aproxima la semana de clases con un desfase de una o dos semanas),
  dia_semana, hora ('HH:MM'), franja ('Mañana' | 'Tarde' | 'Noche' | 'Madrugada'),
  servicio (curso: 'IP', 'EDA', 'IP Honores', 'Deprecated, APO 1', ...),
  tipo_tutoria ('Normal' = 1 hora | 'Express' = 30 minutos | 'Normal pico'),
  categoria_tutor, estado_original,
  estado ('Atendida' | 'No asistió' | 'Cancelada' | 'Cola' = solicitud en lista de espera | 'Cola a reserva' = solicitud de cola que terminó en reserva),
  duracion_minutos, es_prioritaria (0 | 1).
  Tasa de inasistencia = No asistió / (Atendida + No asistió). La cola no ocupa cupo.

v_encuestas — una fila por encuesta respondida.
  id_encuesta, id_reserva, periodo, anio, etapa ('previa' = al reservar | 'posterior' = satisfacción después de la tutoría),
  servicio, tipo_tutoria, calificacion_tutor (1 a 5, solo en 'posterior').

v_respuestas — una fila por respuesta a una pregunta cerrada de una encuesta.
  id_encuesta, periodo, anio, etapa, pregunta (texto completo de la pregunta), respuesta (texto), valor_numerico.
  Para ver qué preguntas existen: SELECT pregunta, etapa, count(*) FROM v_respuestas GROUP BY 1, 2.

agg_tipos_de_horario — reservas por período, tipo de horario y estado, contadas en Silver antes de filtrar.
  periodo, tipo_horario, estado_original, reservas.
  Incluye los tipos que v_reservas deja fuera: 'Deprecated, Grupal', 'Deprecated, Express grupal',
  'Deprecated, Nivelación IP', 'Deprecated, Torre Séneca', 'Entrevistas', 'Sala'.
  Úsala para saber qué tipos de tutoría existieron y hasta cuándo.

agg_oferta_periodo — oferta de cupos por período (categoría Tutor Presencial), resultado de la Entrega 1.
  periodo, capacidad_cupos (cupos disponibles en el semestre), ocupacion_pct (cupos reservados / capacidad; vacío en 201620 y 201710),
  asistencias, en_lista_espera, conversion_cola_pct (porcentaje de la lista de espera que terminó en reserva),
  atenciones_cubiertas_pct (parte de las atenciones del semestre que cubre la categoría; las cifras de 202210 a 202410 cubren 45 % o menos y no son comparables)."""

DESCRIPCION_OFERTA_POR_FRANJA = """
v_oferta_franja — capacidad y ocupación de cada franja (período × día × hora), categoría Tutor Presencial, del reporte de horarios de Bookeau.
  periodo, dia_semana_iso, dia_semana, hora, capacidad_cupos (cupos disponibles de la franja en el semestre), cupos_reservados,
  ocupacion_pct (cupos_reservados / capacidad_cupos; vacía en 201620 y 201710, que no registran cupos reservados),
  asistencias, cancelaciones, inasistencias, en_lista_espera, reservaron_luego_de_lista.
  Úsala para saber qué franjas están llenas o con cupos libres."""

# Sin los archivos de horarios, el agente usa los mismos conteos reconstruidos desde las reservas.
SIN_OFERTA_POR_FRANJA = """
agg_demanda_franja — lo ocurrido en cada franja de atención: período × día de la semana × hora de inicio, categoría Tutor Presencial.
  periodo, dia_semana_iso (1 = lunes), dia_semana, hora ('HH:MM'),
  asistencias, cancelaciones, inasistencias, en_lista_espera, reservaron_luego_de_lista.
  Son los mismos conteos del reporte de horarios de Bookeau (regla R05 de la Entrega 1).
  Esta bodega no tiene la capacidad por franja: solo por período, en agg_oferta_periodo."""


def descripcion() -> str:
    """Descripción de la bodega para el agente; incluye la oferta por franja solo si la bodega la tiene."""
    conexion = sqlite3.connect(f'file:{BODEGA}?mode=ro', uri=True)
    try:
        franjas_con_capacidad, = conexion.execute('SELECT count(*) FROM hecho_oferta').fetchone()
    finally:
        conexion.close()
    return DESCRIPCION + (DESCRIPCION_OFERTA_POR_FRANJA if franjas_con_capacidad else SIN_OFERTA_POR_FRANJA)


def _comprobar_gold(conexion: sqlite3.Connection) -> None:
    grupos = {fila[0] for fila in conexion.execute('SELECT DISTINCT grupo_estado FROM dim_estado')}
    if grupos != GRUPOS_DE_ESTADO:
        raise ValueError(
            f'El Gold no tiene los grupos de estado de la versión final de la Entrega 1 ({sorted(grupos)}). '
            'Vuelve a ejecutar el pipeline de la Entrega 1 (python3 src/main.py) y repite este paso.'
        )


def _cargar_tipos_de_horario(conexion: sqlite3.Connection, reservas: list[dict]) -> int:
    conteo = Counter((fila['periodo_origen'], fila['tipo_horario'], fila['estado_reserva']) for fila in reservas)
    conexion.executescript("""
        DROP TABLE IF EXISTS agg_tipos_de_horario;
        CREATE TABLE agg_tipos_de_horario(
            periodo TEXT NOT NULL, tipo_horario TEXT NOT NULL, estado_original TEXT NOT NULL,
            reservas INTEGER NOT NULL CHECK(reservas > 0),
            PRIMARY KEY(periodo, tipo_horario, estado_original));
    """)
    conexion.executemany('INSERT INTO agg_tipos_de_horario VALUES (?, ?, ?, ?)', [(*clave, n) for clave, n in conteo.items()])
    return sum(conteo.values())


def _medida(estado: str) -> str | None:
    return 'cancelaciones' if estado.startswith('Cancelada') else MEDIDA_DE_LA_FRANJA.get(estado)


def _cargar_demanda_por_franja(conexion: sqlite3.Connection, reservas: list[dict]) -> int:
    """Reconstruye los conteos del reporte de horarios a partir de las reservas (regla R05)."""
    conteo: Counter = Counter()
    for fila in reservas:
        medida = _medida(fila['estado_reserva'])
        if fila['categoria'] == CATEGORIA_DE_LOS_HORARIOS and medida:
            inicio = datetime.fromisoformat(fila['fecha_inicio'])
            conteo[(fila['periodo_origen'], inicio.isoweekday(), inicio.strftime('%H:%M'), medida)] += 1
    franjas = sorted({clave[:3] for clave in conteo})
    conexion.executescript(f"""
        DROP TABLE IF EXISTS agg_demanda_franja;
        CREATE TABLE agg_demanda_franja(
            periodo TEXT NOT NULL, dia_semana_iso INTEGER NOT NULL CHECK(dia_semana_iso BETWEEN 1 AND 7),
            dia_semana TEXT NOT NULL, hora TEXT NOT NULL,
            {', '.join(f'{medida} INTEGER NOT NULL' for medida in MEDIDAS_DE_LA_FRANJA)},
            PRIMARY KEY(periodo, dia_semana_iso, hora));
    """)
    conexion.executemany(
        f'INSERT INTO agg_demanda_franja VALUES (?, ?, ?, ?, {", ".join("?" * len(MEDIDAS_DE_LA_FRANJA))})',
        [(periodo, dia, DIAS[dia], hora, *(conteo[(periodo, dia, hora, medida)] for medida in MEDIDAS_DE_LA_FRANJA))
         for periodo, dia, hora in franjas],
    )
    return len(franjas)


def _cargar_oferta_por_periodo(conexion: sqlite3.Connection) -> int:
    """Carga la oferta por período de la Entrega 1 y comprueba que cuadre con la demanda por franja.

    Los 30 archivos de horarios de Bookeau no están en este repositorio; la capacidad de
    cupos solo se conserva agregada por período, en la tabla de resultados de la Entrega 1.
    Las asistencias y la lista de espera de esa tabla deben coincidir con las que se
    reconstruyen de las reservas: si no, una de las dos fuentes está desactualizada.
    """
    with OFERTA_POR_PERIODO.open(encoding='utf-8') as entrada:
        oferta = list(csv.DictReader(entrada))
    columnas = list(oferta[0])
    conexion.executescript("""
        DROP TABLE IF EXISTS agg_oferta_periodo;
        CREATE TABLE agg_oferta_periodo(
            periodo TEXT PRIMARY KEY, capacidad_cupos INTEGER NOT NULL, ocupacion_pct REAL,
            asistencias INTEGER NOT NULL, en_lista_espera INTEGER NOT NULL,
            conversion_cola_pct REAL, atenciones_cubiertas_pct REAL);
    """)
    conexion.executemany(
        f'INSERT INTO agg_oferta_periodo ({", ".join(columnas)}) VALUES ({", ".join("?" * len(columnas))})',
        [[fila[columna] or None for columna in columnas] for fila in oferta],
    )
    distintos = conexion.execute("""
        SELECT o.periodo FROM agg_oferta_periodo o
        JOIN (SELECT periodo, sum(asistencias) AS asistencias, sum(en_lista_espera) AS en_lista_espera
              FROM agg_demanda_franja GROUP BY periodo) d USING(periodo)
        WHERE o.asistencias <> d.asistencias OR o.en_lista_espera <> d.en_lista_espera
    """).fetchall()
    if distintos:
        raise ValueError(f'La oferta de la Entrega 1 no cuadra con las reservas en los períodos {[p for p, in distintos]}.')
    # Con los archivos de horarios cargados, la capacidad por franja también debe sumar la del período.
    capacidad_distinta = conexion.execute("""
        SELECT a.periodo FROM agg_oferta_periodo a
        JOIN (SELECT p.periodo_original AS periodo, sum(o.cupos_disponibles) AS capacidad
              FROM hecho_oferta o JOIN dim_periodo p ON p.sk_periodo = o.sk_periodo GROUP BY 1) f USING(periodo)
        WHERE a.capacidad_cupos <> f.capacidad
    """).fetchall()
    if capacidad_distinta:
        raise ValueError(f'La capacidad por franja no suma la del período en {[p for p, in capacidad_distinta]}.')
    return len(oferta)


def preparar(gold: Path, silver_reservas: Path) -> None:
    BODEGA.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(gold, BODEGA)
    conexion = sqlite3.connect(BODEGA)
    try:
        _comprobar_gold(conexion)
        # Los comentarios abiertos de las encuestas pueden nombrar a tutores y estudiantes;
        # se quitan de esta copia porque lo que el agente lee se envía a un modelo externo.
        borradas = conexion.execute(
            'DELETE FROM hecho_respuesta WHERE sk_pregunta IN (SELECT sk_pregunta FROM dim_pregunta WHERE es_texto_libre = 1)'
        ).rowcount
        with silver_reservas.open(encoding='utf-8') as entrada:
            reservas = list(csv.DictReader(entrada))
        reservas_silver = _cargar_tipos_de_horario(conexion, reservas)
        franjas = _cargar_demanda_por_franja(conexion, reservas)
        periodos_con_oferta = _cargar_oferta_por_periodo(conexion)
        conexion.executescript((RAIZ / 'sql' / 'bodega_vistas.sql').read_text(encoding='utf-8'))
        conexion.commit()
        conexion.execute('VACUUM')
        reservas_gold, = conexion.execute('SELECT count(*) FROM v_reservas').fetchone()
        franjas_con_capacidad, = conexion.execute('SELECT count(*) FROM v_oferta_franja').fetchone()
    finally:
        conexion.close()
    print(f'{BODEGA.relative_to(RAIZ)}: {reservas_gold} reservas en v_reservas, {reservas_silver} en agg_tipos_de_horario, '
          f'{franjas} franjas en agg_demanda_franja, {periodos_con_oferta} períodos en agg_oferta_periodo '
          f'(cuadran con las reservas), {franjas_con_capacidad} franjas con capacidad en v_oferta_franja, '
          f'{borradas} respuestas de texto libre retiradas')


def _autorizar(accion: int, tabla: str | None, *_: object) -> int:
    if accion == sqlite3.SQLITE_READ and tabla in TABLAS_VEDADAS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def consultar(sql: str) -> dict:
    """Ejecuta una consulta de solo lectura y devuelve columnas y hasta MAX_FILAS filas.

    Los errores de SQL se devuelven como texto para que el agente corrija la consulta.
    """
    sentencia = sql.strip().rstrip(';')
    if ';' in sentencia or not sentencia.lower().startswith(('select', 'with')):
        return {'error': 'Solo se admite una sentencia SELECT (o WITH ... SELECT).'}
    conexion = sqlite3.connect(f'file:{BODEGA}?mode=ro', uri=True)
    conexion.set_authorizer(_autorizar)
    instrucciones = 0

    def cortar_si_es_larga() -> int:
        nonlocal instrucciones
        instrucciones += 1_000_000
        return int(instrucciones > MAX_INSTRUCCIONES_SQLITE)

    conexion.set_progress_handler(cortar_si_es_larga, 1_000_000)
    try:
        cursor = conexion.execute(sentencia)
        filas = cursor.fetchmany(MAX_FILAS + 1)
        return {
            'columnas': [columna[0] for columna in cursor.description],
            'filas': [list(fila) for fila in filas[:MAX_FILAS]],
            'truncado': len(filas) > MAX_FILAS,
        }
    except sqlite3.Error as error:
        return {'error': str(error)}
    finally:
        conexion.close()


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumentos.add_argument('--gold', type=Path, default=PROYECTO_1 / 'data' / 'oro' / 'bookeau.sqlite3')
    argumentos.add_argument('--silver-reservas', type=Path, default=PROYECTO_1 / 'data' / 'plata' / 'reservas.csv')
    opciones = argumentos.parse_args()
    preparar(opciones.gold, opciones.silver_reservas)


if __name__ == '__main__':
    main()
