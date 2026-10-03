"""Create traceable Silver CSVs using only mechanical, documented rules.

No rows are dropped or missing answers imputed. Original business states are preserved;
an additional analytical field applies the documented Finalizada/Realizada rule.
Uses the standard library; run python3 src/limpiar_bookeau.py.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from caracterizar_bookeau import ROOT, SOURCE, DATE_COLUMNS, read_workbook, missing

OUT = ROOT / 'data/plata'
DOCS = ROOT / 'docs/limpieza'
GROUPS = {
    'Reservas': 'reservas',
    'Encuesta Express': 'encuesta_satisfaccion_express',
    'Encuesta Normal': 'encuesta_satisfaccion_normal',
    'Encuesta Reserva Express': 'encuesta_previa_express',
    'Encuesta Reserva Normal IP': 'encuesta_previa_normal_ip',
}
NAMES = {
    'ID': 'id_reserva', 'Fecha inicio': 'fecha_inicio', 'Fecha fin': 'fecha_fin',
    'Fecha de llegada': 'fecha_llegada', 'Fecha de devolución': 'fecha_devolucion',
    'Estado de la reserva': 'estado_reserva', 'Prioritaria': 'prioritaria_original',
    'Categoría': 'categoria', 'Tipo de horario': 'tipo_horario', 'Servicio': 'servicio',
    'Código servicio': 'codigo_servicio', 'Código del servicio': 'codigo_servicio',
    'Usuario': 'usuario', 'Correo usuario': 'correo_usuario', 'Código usuario': 'codigo_usuario',
    'Tipo de usuario': 'tipo_usuario', 'Programa': 'programa',
    'Prestador del servicio': 'prestador_servicio', 'Estado': 'estado_encuesta',
    'Califique la ayuda que le dio su tutor': 'calificacion_ayuda_tutor_original',
}
# Stable question names are based on their full original wording, shared across sources.
def name_for(column):
    if column in NAMES:
        return NAMES[column]
    return 'pregunta_' + hashlib.sha256(column.encode()).hexdigest()[:12]


def encode(value):
    if missing(value):
        return ''
    if isinstance(value, datetime):
        return value.isoformat(sep=' ', timespec='microseconds')
    return str(value)


def normalize_program(value):
    if missing(value):
        return ''
    ascii_label = ''.join(c for c in unicodedata.normalize('NFKD', str(value)) if not unicodedata.combining(c))
    return ' '.join(ascii_label.split()).upper()


def write_csv(path, records, fields=None):
    if not records and not fields:
        return
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    temporary.replace(path)


def clean():
    OUT.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    groups = defaultdict(list)
    mappings, operations, file_counts = [], Counter(), []
    source_programs = defaultdict(Counter)
    schema = {}
    for path in sorted(SOURCE.rglob('*.xlsx')):
        group = path.parent.name
        if group not in GROUPS:
            raise ValueError('Unknown source group; review the cleaning rules: ' + group)
        period = re.search(r'(\d{6})\.xlsx$', path.name).group(1)
        for sheet, headers, rows in read_workbook(path, include_source_row=True):
            current = tuple(headers)
            if group in schema and schema[group] != current:
                raise ValueError('Schema change within group; review: ' + str(path))
            if group not in schema:
                names = [name_for(c) for c in headers]
                if len(set(names)) != len(names):
                    raise ValueError('Canonical column collision: ' + group)
                schema[group] = current
                for original, canonical in zip(headers, names):
                    mappings.append({'grupo': group, 'columna_original': original, 'columna_plata': canonical, 'tipo_lectura_recomendado': 'fecha_hora_sin_zona' if original in DATE_COLUMNS else 'texto', 'regla': 'Alias común para código de servicio' if original in {'Código servicio','Código del servicio'} else 'Nombre canónico; valor original conservado salvo vacío o formato fecha'})
            for row in rows:
                result = {}
                flags = []
                for column in headers:
                    value = row[column]
                    if missing(value):
                        operations[(group,'celda_vacia_o_espacios_a_nulo',column)] += 1
                    if column in DATE_COLUMNS and not missing(value):
                        if isinstance(value,datetime):
                            operations[(group,'fecha_excel_a_iso8601',column)] += 1
                        else:
                            flags.append('fecha_no_interpretable:' + name_for(column))
                    result[name_for(column)] = encode(value)
                result.update(periodo_origen=period, archivo_origen=str(path.relative_to(ROOT)), hoja_origen=sheet, fila_excel=row['__fila_excel__'])
                original_program = encode(row.get('Programa'))
                normalized = normalize_program(row.get('Programa'))
                result['programa_normalizado'] = normalized
                source_programs[group][(original_program,normalized)] += 1
                if original_program != normalized:
                    operations[(group,'programa_normalizado_en_columna_adicional','Programa')] += 1
                priority = encode(row.get('Prioritaria')).strip().casefold()
                priority = ''.join(c for c in unicodedata.normalize('NFKD',priority) if not unicodedata.combining(c))
                result['es_prioritaria'] = 'true' if priority == 'si' else 'false' if priority == 'no' else ''
                if priority not in {'si','no',''}:
                    flags.append('prioridad_fuera_dominio')
                identifier = result['id_reserva']
                if not identifier:
                    flags.append('id_reserva_faltante')
                start,end = row.get('Fecha inicio'),row.get('Fecha fin')
                result['duracion_programada_minutos'] = ''
                if isinstance(start,datetime) and isinstance(end,datetime):
                    duration=(end-start).total_seconds()/60
                    if duration>=0:
                        result['duracion_programada_minutos']=round(duration,6)
                    else:
                        flags.append('fin_anterior_inicio')
                if isinstance(start,datetime) and start.year != int(period[:4]):
                    flags.append('inicio_fuera_anio_periodo')
                arrival = row.get('Fecha de llegada')
                state = row.get('Estado de la reserva')
                # Working rule supplied by María Alejandra Pérez via the user, 2026-10-02.
                # Survey completion is a separate question; do not infer it from this field.
                result['estado_reserva_analitico'] = 'Atendida' if state in {'Finalizada', 'Realizada'} else encode(state)
                if state in {'Finalizada', 'Realizada'}:
                    operations[(group, 'regla_R01_finalizada_realizada_a_atendida', 'Estado de la reserva')] += 1
                if state == 'Finalizada' and missing(arrival):
                    flags.append('revisar_finalizada_sin_llegada')
                elif state == 'No asistió' and not missing(arrival):
                    flags.append('revisar_no_asistio_con_llegada')
                elif isinstance(state,str) and 'cancelada' in state.casefold() and not missing(arrival):
                    flags.append('revisar_cancelacion_con_llegada')
                if group != 'Reservas':
                    survey_state=row.get('Estado')
                    result['marcada_valida_en_origen']='true' if survey_state == 'Válida' else 'false' if survey_state == 'Inválida' else ''
                    # R02: user confirmed exclusion of surveys labelled Inválida, 2026-10-02.
                    result['incluir_encuesta_en_analisis'] = result['marcada_valida_en_origen']
                    result['motivo_exclusion_encuesta'] = 'estado_origen_invalida_R02' if survey_state == 'Inválida' else 'estado_origen_no_reconocido' if survey_state != 'Válida' else ''
                    if survey_state == 'Inválida':
                        operations[(group, 'regla_R02_excluir_encuesta_invalida_de_analisis', 'Estado')] += 1
                    if survey_state == 'Inválida':
                        flags.append('encuesta_marcada_invalida_en_origen')
                    elif survey_state not in {'Válida','Inválida'}:
                        flags.append('estado_encuesta_no_reconocido')
                rating_column='Califique la ayuda que le dio su tutor'
                if rating_column in headers:
                    rating=row.get(rating_column)
                    number=None
                    if not missing(rating):
                        try:
                            numeric=float(rating)
                            if numeric in {1,2,3,4,5}:
                                number=int(numeric)
                            else:
                                flags.append('calificacion_fuera_1_a_5')
                        except (TypeError,ValueError):
                            flags.append('calificacion_no_numerica')
                    result['calificacion_ayuda_tutor']=number if number is not None else ''
                    result['calificacion_en_dominio']='true' if number is not None else 'false' if not missing(rating) else ''
                result['banderas_calidad_json']=json.dumps(flags,ensure_ascii=False)
                groups[group].append(result)
            file_counts.append({'grupo':group,'archivo_origen':str(path.relative_to(ROOT)),'hoja':sheet,'filas_bronce':len(rows),'filas_plata':len(rows)})
    # Reconcile full Silver records without selecting a business truth for conflicting attributes.
    reservation_index=defaultdict(list)
    for row in groups['Reservas']:
        if row['id_reserva']:
            reservation_index[row['id_reserva']].append(row)
    controls=[]
    cases=[]
    for group,rows in groups.items():
        ids=Counter(row['id_reserva'] for row in rows if row['id_reserva'])
        orphan_count,period_mismatch,ambiguous_link = 0,0,0
        for row in rows:
            flags=json.loads(row['banderas_calidad_json'])
            if row['id_reserva'] and ids[row['id_reserva']]>1:
                flags.append('id_repetido_en_grupo')
            if group!='Reservas':
                matched=reservation_index.get(row['id_reserva'],[])
                row['reserva_encontrada']='true' if matched else 'false'
                row['diferencias_con_reserva_json']='[]'
                if not matched:
                    orphan_count+=1
                    flags.append('encuesta_sin_reserva')
                elif len(matched)>1:
                    ambiguous_link+=1
                    flags.append('vinculo_reserva_ambiguo')
                else:
                    canonical=matched[0]
                    if row['periodo_origen']!=canonical['periodo_origen']:
                        period_mismatch+=1
                        flags.append('periodo_diferente_reserva')
                    comparisons=[]
                    for field in [name_for(c) for c in schema['Reservas']]:
                        a,b=row.get(field,''),canonical.get(field,'')
                        if not a or not b:
                            continue
                        equal=a==b
                        if field in {'fecha_inicio','fecha_fin','fecha_llegada','fecha_devolucion'}:
                            try:
                                equal=abs((datetime.fromisoformat(a)-datetime.fromisoformat(b)).total_seconds())<=1
                            except ValueError:
                                pass
                        if not equal:
                            comparisons.append(field)
                    row['diferencias_con_reserva_json']=json.dumps(comparisons,ensure_ascii=False)
                    if comparisons:
                        flags.append('atributos_difieren_de_reserva')
            row['banderas_calidad_json']=json.dumps(flags,ensure_ascii=False)
            for flag in flags:
                cases.append({'grupo':group,'id_reserva':row['id_reserva'],'periodo_origen':row['periodo_origen'],'archivo_origen':row['archivo_origen'],'hoja_origen':row['hoja_origen'],'fila_excel':row['fila_excel'],'bandera':flag,'accion':'Conservar y revisar; no eliminar ni sobrescribir'})
        source_count=sum(f['filas_bronce'] for f in file_counts if f['grupo']==group)
        result={'grupo':group,'archivo_plata':f'data/plata/{GROUPS[group]}.csv','filas_bronce':source_count,'filas_plata':len(rows),'filas_eliminadas':source_count-len(rows),'id_faltantes':len(rows)-sum(ids.values()),'id_distintos':len(ids),'filas_excedentes_id_repetido':sum(count-1 for count in ids.values()),'encuestas_sin_reserva':orphan_count,'vinculos_ambiguos':ambiguous_link,'periodos_diferentes':period_mismatch,'registros_con_banderas':sum(row['banderas_calidad_json']!='[]' for row in rows),'programas_originales_no_vacios':len({a for a,b in source_programs[group] if a}),'programas_normalizados_no_vacios':len({b for a,b in source_programs[group] if b})}
        result['encuestas_incluidas_R02'] = sum(r.get('incluir_encuesta_en_analisis') == 'true' for r in rows) if group != 'Reservas' else ''
        result['encuestas_excluidas_R02'] = sum(r.get('incluir_encuesta_en_analisis') == 'false' for r in rows) if group != 'Reservas' else ''
        result['filas_con_estado_atendida'] = sum(r['estado_reserva_analitico'] == 'Atendida' for r in rows)
        result['conciliacion_estructural']='OK' if source_count==len(rows) and not any(result[k] for k in ['id_faltantes','filas_excedentes_id_repetido','encuestas_sin_reserva','vinculos_ambiguos','periodos_diferentes']) else 'REVISAR'
        controls.append(result)
        write_csv(OUT/f'{GROUPS[group]}.csv',rows)
    write_csv(DOCS/'controles_carga.csv',controls)
    write_csv(DOCS/'conciliacion_archivos.csv',file_counts)
    write_csv(DOCS/'diccionario_columnas.csv',mappings)
    write_csv(DOCS/'bitacora_transformaciones.csv',[{'grupo':g,'regla':rule,'columna_original':col,'celdas':count} for (g,rule,col),count in sorted(operations.items())])
    write_csv(DOCS/'mapa_programas.csv',[{'grupo':g,'programa_original':original,'programa_normalizado':normalized,'filas':count} for g,counts in source_programs.items() for (original,normalized),count in sorted(counts.items())])
    write_csv(DOCS/'casos_revision.csv',cases,['grupo','id_reserva','periodo_origen','archivo_origen','hoja_origen','fila_excel','bandera','accion'])
    flag_counts = Counter((r['grupo'],r['bandera']) for r in cases)
    write_csv(DOCS/'resumen_banderas.csv', [{'grupo':g,'bandera':flag,'registros':n} for (g,flag),n in sorted(flag_counts.items())], ['grupo','bandera','registros'])
    (DOCS/'resumen_limpieza.json').write_text(json.dumps(controls,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(controls,ensure_ascii=False,indent=2))
    return controls


if __name__=='__main__':
    clean()
