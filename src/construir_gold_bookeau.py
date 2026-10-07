"""Full rebuild of the local dimensional model from Silver using SQLite.

Rules applied here: R07 closes the open states (En ejecución, Reservada); R06 groups all cancellation states into one analytic state; R03 keeps only reservations of tutoring sessions (tipo de horario
Normal, Express or Normal pico); R02 keeps only valid surveys, and a survey also needs
its reservation to be in Gold. R04 is materialised as dim_estado.grupo_estado. All survey
dimensions come from the linked reservation; survey-source discrepancies remain
traceable. The offer (horarios) loads hecho_oferta, one row per period, weekday and hour.
The academic period lives only in dim_periodo.
"""
import csv
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from limpiar_bookeau import ROOT, GROUPS

OUT=ROOT/'data/oro'
TUTORIA_TIPOS=('Normal','Express','Normal pico')  # R03
TIPO_PERIODO={'10':'Semestre 1','20':'Semestre 2','19':'Intersemestral'}
NOMBRE_DIA=['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
NOMBRE_MES=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']


def grupo_estado(original,analitico):
    """R04, confirmed by the coordination: the queue never held a slot; open states are not closed outcomes."""
    if analitico=='Atendida':return 'Atendida'
    if analitico=='No asistió':return 'No asistió'
    if original=='En cola':return 'Cola'
    if original=='Cola cancelada por reservación':return 'Cola a reserva'  # the queued request ended in a reservation
    if original.startswith('Cancelada'):return 'Cancelada'
    raise ValueError(f'Estado sin grupo: {original} / {analitico}')


def estado_analitico(r):
    """R01 (Silver) sets Atendida; R06 groups every «Cancelada…» state into one category; R07 closes the
    open states: En ejecución is Atendida, and Reservada is Atendida only with arrival time and provider,
    otherwise No asistió. The original state is kept."""
    original=r['estado_reserva']
    if original.startswith('Cancelada'):return 'Cancelada'
    if original=='En ejecución':return 'Atendida'
    if original=='Reservada':return 'Atendida' if r['fecha_llegada'] and r['prestador_servicio'] else 'No asistió'
    return r['estado_reserva_analitico']


def franja(hora):
    if hora<6:return 'Madrugada'
    if hora<12:return 'Mañana'
    if hora<18:return 'Tarde'
    return 'Noche'
DOCS=ROOT/'docs/artifacts/transformacion'


def load(path):
    with path.open(newline='',encoding='utf-8') as stream:return list(csv.DictReader(stream))


def bool_value(value):
    if value=='true':return 1
    if value=='false':return 0
    return None


def build():
    OUT.mkdir(parents=True,exist_ok=True);DOCS.mkdir(parents=True,exist_ok=True)
    all_reservations=load(ROOT/'data/plata/reservas.csv')
    reservation_index={r['id_reserva']:r for r in all_reservations}
    if len(reservation_index)!=len(all_reservations):raise ValueError('Duplicate reservation IDs')
    reservations=[r for r in all_reservations if r['tipo_horario'] in TUTORIA_TIPOS]  # R03
    included_ids={r['id_reserva'] for r in reservations}
    excluded_r03_reservations=len(all_reservations)-len(reservations)
    horarios_path=ROOT/'data/plata/horarios.csv'
    horarios=load(horarios_path) if horarios_path.exists() else []
    if not reservations:raise ValueError('R03 left no reservations')
    tables={}
    indices={}
    def dimension(name,key_field,attribute_fields,keys,unknown=None):
        unique=sorted(set(keys))
        rows=[];mapping={}
        if unknown is not None:
            unknown=tuple(unknown);mapping[unknown]=0
            rows.append(dict(zip([key_field,*attribute_fields],[0,*unknown])))
            unique=[k for k in unique if k!=unknown]
        for i,key in enumerate(unique,1):
            mapping[key]=i
            rows.append(dict(zip([key_field,*attribute_fields],[i,*key])))
        tables[name]=rows;indices[name]=mapping
        return mapping
    dates=[]
    for r in reservations:
        for field in ['fecha_inicio','fecha_fin','fecha_llegada']:
            if r[field]:dates.append(datetime.fromisoformat(r[field]).date())
    day,last=min(dates),max(dates)
    date_rows=[]
    while day<=last:
        date_rows.append({'sk_fecha':int(day.strftime('%Y%m%d')),'fecha':day.isoformat(),'anio':day.year,'mes':day.month,'dia':day.day,'dia_semana_iso':day.isoweekday(),'nombre_dia':NOMBRE_DIA[day.isoweekday()-1],'nombre_mes':NOMBRE_MES[day.month-1],'es_fin_de_semana':int(day.isoweekday()>5)})
        day+=timedelta(days=1)
    tables['dim_fecha']=date_rows
    tables['dim_hora']=[{'sk_hora':h*60+m+1,'hora':h,'minuto':m,'etiqueta':f'{h:02d}:{m:02d}','franja':franja(h)} for h in range(24) for m in range(60)]
    periods=dimension('dim_periodo','sk_periodo',['periodo_original','anio_codigo','sufijo_original'],[(c,int(c[:4]),c[4:]) for c in sorted({r['periodo_origen'] for r in reservations}|{h['periodo_origen'] for h in horarios})])
    for row in tables['dim_periodo']:row['tipo_periodo']=TIPO_PERIODO.get(row['sufijo_original'],'Sin clasificar')
    tables['dim_dia_semana']=[{'sk_dia_semana':i,'dia_semana_iso':i,'nombre_dia':NOMBRE_DIA[i-1],'es_fin_de_semana':int(i>5)} for i in range(1,8)]
    services=dimension('dim_servicio','sk_servicio',['codigo_servicio','servicio_original'],[(r['codigo_servicio'],r['servicio']) for r in reservations])
    modes=dimension('dim_modalidad','sk_modalidad',['tipo_horario_original','categoria_original'],[(r['tipo_horario'],r['categoria']) for r in reservations])
    states=dimension('dim_estado','sk_estado',['estado_original','estado_analitico'],[(r['estado_reserva'],estado_analitico(r)) for r in reservations])
    for row in tables['dim_estado']:row['grupo_estado']=grupo_estado(row['estado_original'],row['estado_analitico'])
    programs=dimension('dim_programa','sk_programa',['programa_normalizado'],[(r['programa_normalizado'] or 'No informado',) for r in reservations],unknown=('No informado',))
    survey_types=dimension('dim_tipo_encuesta','sk_tipo_encuesta',['grupo_fuente','etapa'],[(g,'posterior' if 'satisfaccion' in f else 'previa') for g,f in GROUPS.items() if g!='Reservas'])
    mapping=load(ROOT/'docs/artifacts/limpieza/diccionario_columnas.csv')
    survey_question_map=defaultdict(list)
    question_attributes={}
    for r in mapping:
        column=r['columna_plata'];prompt=r['columna_original']
        if column.startswith('pregunta_') or column=='calificacion_ayuda_tutor_original':
            survey_question_map[r['grupo']].append(column)
            free=prompt.lower().startswith(('comente','escriba','sugerencias','indique cuál'))
            question_attributes[column]=(column,prompt,int(free),int(column=='calificacion_ayuda_tutor_original'))
    questions=dimension('dim_pregunta','sk_pregunta',['columna_plata','texto_pregunta','es_texto_libre','es_calificacion_tutor'],question_attributes.values())
    question_keys={r['columna_plata']:r['sk_pregunta'] for r in tables['dim_pregunta']}
    def keys(r):
        start=datetime.fromisoformat(r['fecha_inicio'])
        return {'sk_fecha_inicio':int(start.strftime('%Y%m%d')),'sk_hora_inicio':start.hour*60+start.minute+1,'sk_periodo':periods[(r['periodo_origen'],int(r['periodo_origen'][:4]),r['periodo_origen'][4:])],'sk_servicio':services[(r['codigo_servicio'],r['servicio'])],'sk_modalidad':modes[(r['tipo_horario'],r['categoria'])],'sk_estado':states[(r['estado_reserva'],estado_analitico(r))],'sk_programa':programs[(r['programa_normalizado'] or 'No informado',)]}
    fact_reservations=[]
    for r in reservations:
        k=keys(r)
        row={'id_reserva':r['id_reserva'],**k,'sk_fecha_fin':int(datetime.fromisoformat(r['fecha_fin']).strftime('%Y%m%d')),'sk_fecha_llegada':int(datetime.fromisoformat(r['fecha_llegada']).strftime('%Y%m%d')) if r['fecha_llegada'] else None,'fecha_inicio':r['fecha_inicio'],'fecha_fin':r['fecha_fin'],'fecha_llegada':r['fecha_llegada'] or None,'duracion_programada_minutos':float(r['duracion_programada_minutos']) if r['duracion_programada_minutos'] else None,'es_prioritaria':bool_value(r['es_prioritaria']),'evento_reserva':1,'archivo_origen':r['archivo_origen'],'hoja_origen':r['hoja_origen'],'fila_excel':int(r['fila_excel']),'banderas_calidad_json':r['banderas_calidad_json']}
        fact_reservations.append(row)
    tables['hecho_reserva']=fact_reservations
    fact_surveys=[];fact_answers=[];reconciliation=[]
    for group,filename in GROUPS.items():
        if group=='Reservas':continue
        rows=load(ROOT/'data/plata'/f'{filename}.csv')
        before=len(fact_surveys);excluded=0;excluded_r03=0;pending=0;expected_answers=0
        seen=set()
        for r in rows:
            if r['id_reserva'] in seen:raise ValueError('Repeated survey grain')
            seen.add(r['id_reserva'])
            if r['incluir_encuesta_en_analisis']!='true':
                if r['incluir_encuesta_en_analisis']=='false':excluded+=1
                else:pending+=1
                continue
            canonical=reservation_index[r['id_reserva']]
            if canonical['periodo_origen']!=r['periodo_origen']:raise ValueError('Period mismatch')
            if r['id_reserva'] not in included_ids:
                excluded_r03+=1  # R03: the survey belongs to a reservation that is not a tutoring session
                continue
            identifier=filename+':'+r['id_reserva']
            survey={'id_encuesta':identifier,'id_reserva':r['id_reserva'],'sk_tipo_encuesta':survey_types[(group,'posterior' if 'satisfaccion' in filename else 'previa')],**keys(canonical),'calificacion_ayuda_tutor':int(r['calificacion_ayuda_tutor']) if r.get('calificacion_ayuda_tutor') else None,'respuesta_encuesta':1,'archivo_origen':r['archivo_origen'],'hoja_origen':r['hoja_origen'],'fila_excel':int(r['fila_excel']),'banderas_calidad_json':r['banderas_calidad_json'],'diferencias_con_reserva_json':r['diferencias_con_reserva_json']}
            fact_surveys.append(survey)
            for column in survey_question_map[group]:
                value=r[column]
                if not value.strip():continue
                expected_answers+=1
                numeric=None
                if column=='calificacion_ayuda_tutor_original' and r.get('calificacion_ayuda_tutor'):
                    numeric=int(r['calificacion_ayuda_tutor'])
                fact_answers.append({'id_encuesta':identifier,'sk_pregunta':question_keys[column],'valor_original':value,'valor_numerico':numeric,'respuesta_item':1})
        included=len(fact_surveys)-before
        if included+excluded+excluded_r03+pending!=len(rows):raise ValueError('Survey counts do not reconcile')
        reconciliation.append({'grupo':group,'filas_silver':len(rows),'encuestas_gold':included,'excluidas_R02':excluded,'excluidas_R03':excluded_r03,'estado_desconocido_pendiente':pending,'items_no_vacios':expected_answers,'conciliacion':'OK'})
    tables['hecho_encuesta']=fact_surveys;tables['hecho_respuesta']=fact_answers
    measures=['asistencias','cancelaciones','inasistencias','en_lista_espera','reservaron_luego_de_lista','cupos_reservados','cupos_disponibles']
    tables['hecho_oferta']=[{'sk_periodo':periods[(h['periodo_origen'],int(h['periodo_origen'][:4]),h['periodo_origen'][4:])],'sk_dia_semana':int(h['dia_semana_iso']),
        'sk_hora_inicio':int(h['hora_inicio'][:2])*60+int(h['hora_inicio'][3:])+1,**{m:int(h[m]) for m in measures},
        'archivo_origen':h['archivo_origen'],'hoja_origen':h['hoja_origen'],'fila_excel':int(h['fila_excel']),'banderas_calidad_json':h['banderas_calidad_json']} for h in horarios]
    temporary=OUT/'bookeau.sqlite3.tmp'
    if temporary.exists():temporary.unlink()
    db=sqlite3.connect(temporary)
    try:
        db.executescript((ROOT/'sql/00_crear_modelo.sql').read_text())
        for table,rows in tables.items():
            if not rows:continue
            fields=list(rows[0]);placeholders=','.join('?' for _ in fields)
            db.executemany(f"INSERT INTO {table} ({','.join(fields)}) VALUES ({placeholders})",[tuple(r[f] for f in fields) for r in rows])
        if list(db.execute('PRAGMA foreign_key_check')):raise ValueError('Foreign keys failed')
        if db.execute('SELECT COUNT(*) FROM hecho_reserva').fetchone()[0]!=len(reservations):raise ValueError('Reservation counts differ')
        if len(reservations)+excluded_r03_reservations!=len(all_reservations):raise ValueError('R03 counts do not reconcile')
        if db.execute('SELECT COUNT(*) FROM hecho_encuesta').fetchone()[0]!=sum(r['encuestas_gold'] for r in reconciliation):raise ValueError('Survey counts differ')
        if db.execute('SELECT COUNT(*) FROM hecho_oferta').fetchone()[0]!=len(horarios):raise ValueError('Offer counts differ')
        db.commit()
    except Exception:
        db.close();temporary.unlink(missing_ok=True);raise
    db.close();temporary.replace(OUT/'bookeau.sqlite3')
    for table,rows in tables.items():
        if not rows:continue
        with (OUT/f'{table}.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    with (DOCS/'conciliacion_silver_gold.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(reconciliation[0]));writer.writeheader();writer.writerows(reconciliation)
    counts={table:len(rows) for table,rows in tables.items()}
    controls={'conteos':counts,'reservas_silver':len(all_reservations),'reservas_excluidas_R03':excluded_r03_reservations,'reservas_gold':len(fact_reservations),'franjas_oferta_silver':len(horarios),'franjas_oferta_gold':len(tables['hecho_oferta']),'encuestas_excluidas_R03':sum(r['excluidas_R03'] for r in reconciliation),'atenciones':sum(estado_analitico(r)=='Atendida' for r in reservations),'encuestas_excluidas_R02':sum(r['excluidas_R02'] for r in reconciliation),'claves_foraneas':'OK','unicidad_granos':'OK','conciliacion':'OK'}
    (DOCS/'controles_gold.json').write_text(json.dumps(controls,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(controls,ensure_ascii=False,indent=2))


if __name__=='__main__':build()
