"""Build question-specific quality evidence and descriptive analysis inputs.

No attendance classification or historical category equivalences are assumed.
Original workbooks remain unchanged. Uses the standard library only.
"""
import csv
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from caracterizar_bookeau import read_workbook, missing, SOURCE, ROOT

OUT = ROOT / 'docs/artifacts/calidad'
RATING = 'Califique la ayuda que le dio su tutor'


def write_csv(name, rows, fields=None):
    if not rows and fields is None:
        return
    with (OUT / name).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def rating_value(value):
    if missing(value):
        return None
    try:
        number = float(value)
        return int(number) if number in {1, 2, 3, 4, 5} else None
    except (TypeError, ValueError):
        return None


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    reservations = {}
    survey_rows = []
    for path in sorted(SOURCE.rglob('*.xlsx')):
        period = path.stem[-6:]
        for _, _, rows in read_workbook(path):
            if path.parent.name == 'Reservas':
                for row in rows:
                    if row['ID'] in reservations:
                        raise ValueError('Reservation ID is not unique; reassess joins before proceeding.')
                    reservations[row['ID']] = (period, row)
            elif path.parent.name in {'Encuesta Express', 'Encuesta Normal'}:
                survey_rows.extend((path.parent.name, period, row) for row in rows)
    demand = Counter()
    slots = Counter()
    quality_cases = []
    for identifier, (period, row) in reservations.items():
        start = row['Fecha inicio']
        demand[(period, row['Tipo de horario'], row['Servicio'], row['Estado de la reserva'])] += 1
        if isinstance(start, datetime):
            slots[(period, row['Tipo de horario'], row['Servicio'], start.weekday()+1, start.hour)] += 1
        state, arrival = row['Estado de la reserva'], row['Fecha de llegada']
        flag = None
        if state == 'Finalizada' and missing(arrival):
            flag = 'Finalizada sin marca de llegada'
        elif state == 'No asistió' and not missing(arrival):
            flag = 'No asistió con marca de llegada'
        elif ('Cancelada' in state or 'cancelada' in state) and not missing(arrival):
            flag = 'Estado de cancelación con marca de llegada'
        if flag:
            quality_cases.append({'id_reserva': identifier, 'periodo':period,'estado_reserva':state,'motivo_revision':flag,'tratamiento':'Conservar; confirmar significado operativo antes de corregir o excluir'})
    write_csv('demanda_por_periodo_modalidad_servicio_estado.csv', [dict(zip(['periodo','tipo_horario_original','servicio_original','estado_reserva_original','eventos_reserva'], (*key, value))) for key,value in sorted(demand.items())])
    write_csv('agenda_por_dia_hora.csv', [dict(zip(['periodo','tipo_horario_original','servicio_original','dia_semana_iso','hora_inicio','eventos_reserva'], (*key, value))) for key,value in sorted(slots.items())])
    write_csv('casos_revision_estado_llegada.csv',quality_cases,['id_reserva','periodo','estado_reserva','motivo_revision','tratamiento'])
    observations = defaultdict(list)
    seen_survey_ids = defaultdict(set)
    for group, period, survey in survey_rows:
        identifier = survey['ID']
        if identifier in seen_survey_ids[group]:
            raise ValueError('Survey ID is not unique within its group; reassess grain.')
        seen_survey_ids[group].add(identifier)
        if identifier not in reservations:
            raise ValueError('Survey lacks a corresponding reservation; reassess linkage.')
        reservation_period, canonical = reservations[identifier]
        if period != reservation_period:
            raise ValueError('Survey and reservation periods differ; reassess time attribution.')
        # Keep source survey group and actual reservation modality separately.
        key=(group,period,canonical['Tipo de horario'],canonical['Servicio'])
        observations[key].append((survey,canonical))
    results=[]
    for key,pairs in sorted(observations.items()):
        valid=[survey for survey,_ in pairs if survey.get('Estado')=='Válida']
        values=[rating_value(s.get(RATING)) for s in valid]
        ratings=[v for v in values if v is not None]
        counts=Counter(ratings)
        results.append({'grupo_encuesta':key[0],'periodo':key[1],'tipo_horario_reserva':key[2],'servicio_reserva':key[3],'respuestas_exportadas':len(pairs),'respuestas_marcadas_valida':len(valid),'respuestas_otro_estado':len(pairs)-len(valid),'calificaciones_1_a_5_en_validas':len(ratings),'sin_calificacion_en_validas':sum(missing(s.get(RATING)) for s in valid),'fuera_dominio_en_validas':sum(not missing(s.get(RATING)) and rating_value(s.get(RATING)) is None for s in valid),'completitud_item_en_validas_pct':round(100*len(ratings)/len(valid),4) if valid else '', 'media_descriptiva_provisional':round(statistics.mean(ratings),4) if ratings else '', 'mediana_descriptiva_provisional':statistics.median(ratings) if ratings else '', **{f'n_calificacion_{i}':counts[i] for i in range(1,6)}})
    write_csv('satisfaccion_por_periodo_modalidad_servicio.csv',results)
    comparable=defaultdict(dict)
    for row in results:
        expected_group={'Express':'Encuesta Express','Normal':'Encuesta Normal'}.get(row['tipo_horario_reserva'])
        if row['grupo_encuesta']==expected_group and row['calificaciones_1_a_5_en_validas']:
            comparable[(row['periodo'],row['servicio_reserva'])][row['tipo_horario_reserva']]=row
    matched=[]
    for (period,service),modes in sorted(comparable.items()):
        if set(modes)=={'Express','Normal'}:
            e,n=modes['Express'],modes['Normal']
            matched.append({'periodo':period,'servicio_original':service,'n_express':e['calificaciones_1_a_5_en_validas'],'n_normal':n['calificaciones_1_a_5_en_validas'],'media_express_provisional':e['media_descriptiva_provisional'],'media_normal_provisional':n['media_descriptiva_provisional'],'completitud_item_express_pct':e['completitud_item_en_validas_pct'],'completitud_item_normal_pct':n['completitud_item_en_validas_pct'],'limite':'Misma pregunta/periodo/servicio; no garantiza equivalencia histórica, ausencia de sesgo ni efecto causal'})
    write_csv('estratos_comunes_express_normal.csv',matched,['periodo','servicio_original','n_express','n_normal','media_express_provisional','media_normal_provisional','completitud_item_express_pct','completitud_item_normal_pct','limite'])
    survey_summary=[]
    for group in sorted({g for g,_,_ in survey_rows}):
        rows=[s for g,_,s in survey_rows if g==group]
        valid=[s for s in rows if s.get('Estado')=='Válida']
        counted=[rating_value(s.get(RATING)) for s in valid]
        survey_summary.append({'grupo':group,'respuestas':len(rows),'marcadas_valida':len(valid),'otro_estado':len(rows)-len(valid),'calificaciones_validas_1_a_5':sum(v is not None for v in counted),'faltantes_en_validas':sum(missing(s.get(RATING)) for s in valid),'fuera_dominio_en_validas':sum(not missing(s.get(RATING)) and rating_value(s.get(RATING)) is None for s in valid)})
    write_csv('resumen_elegibilidad_satisfaccion.csv',survey_summary)
    facts={'reservas':len(reservations),'estratos_periodo_servicio_con_ambas_modalidades_y_calificacion':len(matched),'casos_revision_estado_llegada':len(quality_cases),'motivos_revision':dict(Counter(r['motivo_revision'] for r in quality_cases)), 'satisfaccion':survey_summary,'tipos_horario_en_encuestas':{g:dict(Counter(r['Tipo de horario'] for group,_,r in survey_rows if group==g)) for g in sorted({g for g,_,_ in survey_rows})}}
    (OUT/'resumen_preparacion.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(facts,ensure_ascii=False,indent=2))


if __name__=='__main__':
    prepare()
