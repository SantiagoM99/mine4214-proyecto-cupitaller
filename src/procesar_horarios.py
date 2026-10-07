"""Procesa los horarios de CupiTaller (oferta por semestre) de Bronze a Silver y los concilia con Reservas.

Cada libro `horariosYYYYPP.xlsx` resume un semestre por franja semanal (día y hora): asistencias,
cancelaciones, inasistencias, lista de espera, reservas hechas luego de estar en lista, y cupos
reservados y disponibles. No tiene ID de reserva ni datos personales.

Salidas:
  data/plata/horarios.csv                                         Silver, una fila por período, día y hora
  docs/artifacts/limpieza/horarios_archivos.csv                   filas por archivo (incluye los vacíos)
  docs/artifacts/caracterizacion/horarios_por_periodo.csv         perfil por período
  docs/artifacts/calidad/reconciliacion_horarios_reservas.csv     coincidencia con Reservas por período
  docs/artifacts/calidad/reconciliacion_horarios_detalle.csv      franjas con diferencias

Debe ejecutarse después de limpiar_bookeau.py, porque concilia con data/plata/reservas.csv.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime

from caracterizar_bookeau import ROOT, SOURCE, read_workbook
from limpiar_bookeau import OUT as SILVER, write_csv

CARPETA = 'horarios'
DOCS_LIMPIEZA = ROOT / 'docs/artifacts/limpieza'
DOCS_CARACTERIZACION = ROOT / 'docs/artifacts/caracterizacion'
DOCS_CALIDAD = ROOT / 'docs/artifacts/calidad'
DIAS = {'lunes': 1, 'martes': 2, 'miércoles': 3, 'miercoles': 3, 'jueves': 4, 'viernes': 5, 'sábado': 6, 'sabado': 6, 'domingo': 7}
MEDIDAS = {
    'Asistencias': 'asistencias', 'Cancelaciones': 'cancelaciones', 'Inasistencias': 'inasistencias',
    'En lista de espera': 'en_lista_espera', 'Reservaron luego de estar en lista': 'reservaron_luego_de_lista',
    'Cupos reservados': 'cupos_reservados', 'Cupos disponibles': 'cupos_disponibles',
}
ENCABEZADOS = ['Día', 'Hora', *MEDIDAS]
# R05: el reporte de horarios cubre solo la categoría Tutor Presencial. Con ella, cada medida
# coincide con la suma de estados de Reservas que se indica aquí.
CATEGORIA_HORARIOS = 'Tutor Presencial'
CONCILIACION = {
    'asistencias': lambda e: e in ('Finalizada', 'Realizada', 'En ejecución'),
    'inasistencias': lambda e: e == 'No asistió',
    'cancelaciones': lambda e: e.startswith('Cancelada'),
    'en_lista_espera': lambda e: e == 'En cola',
    'reservaron_luego_de_lista': lambda e: e == 'Cola cancelada por reservación',
}
CAMPOS = ['periodo_origen', 'dia_semana_iso', 'dia_original', 'hora_inicio', 'hora_original', *MEDIDAS.values(),
          'archivo_origen', 'hoja_origen', 'fila_excel', 'banderas_calidad_json']


def hora_24(texto: str) -> str:
    """'9:00 am' -> '09:00'; '12:30 pm' -> '12:30'."""
    m = re.fullmatch(r'\s*(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\.?\s*', str(texto).lower())
    if not m:
        raise ValueError(f'Hora no reconocida en horarios: {texto!r}')
    hora, minuto = int(m.group(1)) % 12, int(m.group(2))
    if m.group(3) == 'p':
        hora += 12
    return f'{hora:02d}:{minuto:02d}'


def leer():
    carpeta = SOURCE / CARPETA
    if not carpeta.is_dir():
        raise SystemExit(f'No existe {carpeta.relative_to(ROOT)}: no hay horarios para procesar.')
    filas, archivos = [], []
    for path in sorted(carpeta.glob('*.xlsx')):
        periodo = re.search(r'(\d{6})\.xlsx$', path.name).group(1)
        for hoja, encabezados, registros in read_workbook(path, include_source_row=True):
            if encabezados != ENCABEZADOS:
                raise ValueError(f'Encabezados inesperados en {path.name}: {encabezados}')
            archivos.append({'periodo': periodo, 'archivo_origen': str(path.relative_to(ROOT)), 'hoja': hoja, 'filas': len(registros)})
            for r in registros:
                banderas = []
                dia = str(r['Día']).strip()
                dia_iso = DIAS[dia.lower()]
                if dia_iso > 5:
                    banderas.append('dia_fuera_de_lunes_a_viernes')
                medidas = {nombre: r[original] for original, nombre in MEDIDAS.items()}
                if any(v is None or v < 0 for v in medidas.values()):
                    banderas.append('medida_vacia_o_negativa')
                filas.append({
                    'periodo_origen': periodo, 'dia_semana_iso': dia_iso, 'dia_original': dia,
                    'hora_inicio': hora_24(r['Hora']), 'hora_original': r['Hora'],
                    **{k: ('' if v is None else v) for k, v in medidas.items()},
                    'archivo_origen': str(path.relative_to(ROOT)), 'hoja_origen': hoja, 'fila_excel': r['__fila_excel__'],
                    'banderas_calidad_json': json.dumps(banderas, ensure_ascii=False)})
    claves = Counter((f['periodo_origen'], f['dia_semana_iso'], f['hora_inicio']) for f in filas)
    repetidas = [k for k, n in claves.items() if n > 1]
    if repetidas:
        raise ValueError(f'Franjas repetidas en horarios (período, día, hora): {repetidas[:5]}')
    return filas, archivos


def perfil(filas):
    por_periodo = defaultdict(lambda: Counter())
    for f in filas:
        c = por_periodo[f['periodo_origen']]
        c['franjas'] += 1
        for m in MEDIDAS.values():
            c[m] += f[m] or 0
        c['franjas_sin_cupos_reservados'] += not f['cupos_reservados']
    return [{'periodo': p, **{k: c[k] for k in ['franjas', *MEDIDAS.values(), 'franjas_sin_cupos_reservados']}} for p, c in sorted(por_periodo.items())]


def conciliar(filas):
    reservas = SILVER / 'reservas.csv'
    if not reservas.exists():
        raise SystemExit('Falta data/plata/reservas.csv: ejecuta antes limpiar_bookeau.py.')
    esperado = defaultdict(Counter)
    with reservas.open(newline='', encoding='utf-8') as stream:
        for r in csv.DictReader(stream):
            if r['categoria'] != CATEGORIA_HORARIOS:
                continue
            inicio = datetime.fromisoformat(r['fecha_inicio'])
            clave = (r['periodo_origen'], inicio.isoweekday(), inicio.strftime('%H:%M'))
            for medida, regla in CONCILIACION.items():
                if regla(r['estado_reserva']):
                    esperado[clave][medida] += 1
            esperado[clave]['_eventos'] += 1
    resumen, detalle = defaultdict(Counter), []
    for f in filas:
        clave = (f['periodo_origen'], f['dia_semana_iso'], f['hora_inicio'])
        r = resumen[f['periodo_origen']]
        r['franjas'] += 1
        diferencias = {m: (f[m] or 0) - esperado[clave][m] for m in CONCILIACION if (f[m] or 0) != esperado[clave][m]}
        r['franjas_coinciden'] += not diferencias
        for m in CONCILIACION:
            r['horarios_' + m] += f[m] or 0
            r['reservas_' + m] += esperado[clave][m]
        if diferencias:
            detalle.append({'periodo': clave[0], 'dia_semana_iso': clave[1], 'hora_inicio': clave[2],
                            **{f'dif_{m}': (f[m] or 0) - esperado[clave][m] for m in CONCILIACION}})
    en_horarios = {(f['periodo_origen'], f['dia_semana_iso'], f['hora_inicio']) for f in filas}
    periodos_horarios = {f['periodo_origen'] for f in filas}
    for clave, c in esperado.items():
        if clave[0] in periodos_horarios and clave not in en_horarios:
            resumen[clave[0]]['franjas_en_reservas_sin_fila_en_horarios'] += 1
    for periodo in {p for p, _, _ in esperado} - periodos_horarios:
        resumen[periodo]['sin_archivo_de_horarios'] = 1
    cabecera = ['franjas', 'franjas_coinciden', 'franjas_en_reservas_sin_fila_en_horarios', 'sin_archivo_de_horarios']
    cabecera += [f'{o}_{m}' for m in CONCILIACION for o in ('horarios', 'reservas')]
    filas_resumen = [{'periodo': p, **{k: resumen[p][k] for k in cabecera}, 'pct_franjas_coinciden': round(100 * resumen[p]['franjas_coinciden'] / resumen[p]['franjas'], 1) if resumen[p]['franjas'] else ''}
                     for p in sorted(resumen)]
    return filas_resumen, detalle


def main():
    for carpeta in (SILVER, DOCS_LIMPIEZA, DOCS_CARACTERIZACION, DOCS_CALIDAD):
        carpeta.mkdir(parents=True, exist_ok=True)
    filas, archivos = leer()
    write_csv(SILVER / 'horarios.csv', filas, CAMPOS)
    write_csv(DOCS_LIMPIEZA / 'horarios_archivos.csv', archivos)
    write_csv(DOCS_CARACTERIZACION / 'horarios_por_periodo.csv', perfil(filas))
    resumen, detalle = conciliar(filas)
    write_csv(DOCS_CALIDAD / 'reconciliacion_horarios_reservas.csv', resumen)
    write_csv(DOCS_CALIDAD / 'reconciliacion_horarios_detalle.csv', detalle, ['periodo', 'dia_semana_iso', 'hora_inicio', *[f'dif_{m}' for m in CONCILIACION]])
    vacios = [a['periodo'] for a in archivos if a['filas'] == 0]
    con_filas = [r for r in resumen if r['franjas']]
    total = sum(r['franjas'] for r in con_filas)
    coinciden = sum(r['franjas_coinciden'] for r in con_filas)
    print(json.dumps({'archivos': len(archivos), 'archivos_vacios': vacios, 'franjas': len(filas),
                      'franjas_que_coinciden_con_reservas': f'{coinciden} de {total}',
                      'periodos_solo_en_horarios': [r['periodo'] for r in resumen if r['periodo'] not in {a['periodo'] for a in archivos if a['filas'] == 0} and r['franjas'] and r['reservas_asistencias'] == 0 and r['horarios_asistencias'] > 0]},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
