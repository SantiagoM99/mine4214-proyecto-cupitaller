"""Assess whether reservation states distinguish survey availability/completeness.

Reads Silver. A missing exported survey is not proof that an invited user failed
 to respond. No separate tutor survey source exists in the shared package.
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from limpiar_bookeau import ROOT, GROUPS

OUT=ROOT/'docs/calidad/estados_encuestas'


def read(path):
    with path.open(newline='',encoding='utf-8') as stream:
        yield from csv.DictReader(stream)


def write(name,rows):
    if not rows:
        return
    with (OUT/name).open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def ratio(a,b):
    return round(100*a/b,4) if b else ''


def check():
    OUT.mkdir(parents=True,exist_ok=True)
    reservations={}
    for row in read(ROOT/'data/plata/reservas.csv'):
        identifier=row['id_reserva']
        if identifier in reservations:
            raise ValueError('Duplicate reservation key')
        reservations[identifier]={k:row[k] for k in ['estado_reserva','periodo_origen','tipo_horario','servicio']}
    surveys=defaultdict(dict)
    content_cases=[]
    cross_states=Counter()
    for group,filename in GROUPS.items():
        if group=='Reservas':continue
        for row in read(ROOT/'data/plata'/f'{filename}.csv'):
            identifier=row['id_reserva']
            if identifier not in reservations or identifier in surveys[group]:
                raise ValueError('Survey link is absent or duplicated within group')
            if row['periodo_origen'] != reservations[identifier]['periodo_origen']:
                raise ValueError('Survey and reservation periods differ')
            question_columns=[c for c in row if c.startswith('pregunta_') or c=='calificacion_ayuda_tutor_original']
            answered=sum(bool(row[c].strip()) for c in question_columns)
            if answered == 0:
                content_cases.append({'fuente':filename,'id_reserva':identifier,'estado_en_reservas':reservations[identifier]['estado_reserva'],'estado_encuesta':row['estado_encuesta'],'periodo':row['periodo_origen'],'archivo_origen':row['archivo_origen'],'hoja_origen':row['hoja_origen'],'fila_excel':row['fila_excel'],'interpretacion':'Sin contenido en preguntas exportadas; obligatoriedad e instrumento histórico pendientes de confirmar'})
            surveys[group][identifier]={'estado_encuesta':row['estado_encuesta'],'preguntas_exportadas':len(question_columns),'preguntas_no_vacias':answered,'calificacion_presente':bool(row.get('calificacion_ayuda_tutor_original','').strip()),'estado_reserva_en_encuesta':row['estado_reserva']}
            cross_states[(group,reservations[identifier]['estado_reserva'],row['estado_reserva'])]+=1
    states=sorted({r['estado_reserva'] for r in reservations.values()})
    post=set(surveys['Encuesta Express'])|set(surveys['Encuesta Normal'])
    pre=set(surveys['Encuesta Reserva Express'])|set(surveys['Encuesta Reserva Normal IP'])
    summary=[]
    for state in states:
        identifiers={key for key,r in reservations.items() if r['estado_reserva']==state}
        total=len(identifiers)
        with_post=len(identifiers&post)
        with_pre=len(identifiers&pre)
        summary.append({'estado_en_reservas':state,'eventos':total,'con_encuesta_posterior_exportada':with_post,'sin_encuesta_posterior_exportada':total-with_post,'pct_con_posterior_exportada':ratio(with_post,total),'con_encuesta_previa_exportada':with_pre,'pct_con_previa_exportada':ratio(with_pre,total)})
    detail=[]
    for group,mapping in surveys.items():
        for state in states:
            identifiers=[key for key in mapping if reservations[key]['estado_reserva']==state]
            if not identifiers:continue
            entries=[mapping[key] for key in identifiers]
            total=len(entries)
            detail.append({'grupo_encuesta':group,'estado_en_reservas':state,'respuestas_exportadas':total,'marcadas_valida':sum(r['estado_encuesta']=='Válida' for r in entries),'marcadas_invalida':sum(r['estado_encuesta']=='Inválida' for r in entries),'sin_ninguna_respuesta_a_preguntas':sum(r['preguntas_no_vacias']==0 for r in entries),'con_alguna_respuesta':sum(r['preguntas_no_vacias']>0 for r in entries),'con_todas_preguntas_exportadas_no_vacias':sum(r['preguntas_no_vacias']==r['preguntas_exportadas'] for r in entries),'con_calificacion_no_vacia':sum(r['calificacion_presente'] for r in entries) if group in {'Encuesta Express','Encuesta Normal'} else ''})
    strata=defaultdict(lambda:[0,0])
    for identifier,r in reservations.items():
        key=(r['periodo_origen'],r['tipo_horario'],r['servicio'],r['estado_reserva'])
        strata[key][0]+=1
        strata[key][1]+=identifier in post
    strata_rows=[dict(zip(['periodo','tipo_horario','servicio','estado_en_reservas','eventos','con_posterior_exportada','pct_con_posterior_exportada'],(*key,n,m,ratio(m,n)))) for key,(n,m) in sorted(strata.items())]
    comparable=[]
    bases={key[:3] for key in strata}
    for period,mode,service in sorted(bases):
        a=strata.get((period,mode,service,'Finalizada'))
        b=strata.get((period,mode,service,'Realizada'))
        if a and b:
            comparable.append({'periodo':period,'tipo_horario':mode,'servicio':service,'finalizadas':a[0],'finalizadas_con_posterior':a[1],'pct_finalizadas_con_posterior':ratio(a[1],a[0]),'realizadas':b[0],'realizadas_con_posterior':b[1],'pct_realizadas_con_posterior':ratio(b[1],b[0]),'diferencia_puntos_pct':round(100*a[1]/a[0]-100*b[1]/b[0],4)})
    cross_rows=[{'grupo_encuesta':g,'estado_en_reservas':a,'estado_en_encuesta':b,'filas':n} for (g,a,b),n in sorted(cross_states.items())]
    by_period=defaultdict(lambda:[0,0])
    for identifier,r in reservations.items():
        if r['estado_reserva'] in {'Finalizada','Realizada'}:
            key=(r['periodo_origen'],r['estado_reserva'])
            by_period[key][0]+=1;by_period[key][1]+=identifier in post
    write('resumen_por_estado.csv',summary)
    write('casos_encuesta_sin_respuestas.csv',content_cases)
    write('validez_completitud_por_estado.csv',detail)
    write('cobertura_por_periodo_modalidad_servicio_estado.csv',strata_rows)
    write('comparacion_estratos_comunes.csv',comparable)
    write('estados_reserva_vs_encuesta.csv',cross_rows)
    write('cobertura_por_periodo_estado.csv',[{'periodo':p,'estado':s,'eventos':n,'con_posterior':m,'pct_con_posterior':ratio(m,n)} for (p,s),(n,m) in sorted(by_period.items())])
    compact={'estados_objetivo':[r for r in summary if r['estado_en_reservas'] in {'Finalizada','Realizada'}],'detalle_encuestas':[r for r in detail if r['estado_en_reservas'] in {'Finalizada','Realizada'}],'estratos_con_ambos_estados':len(comparable),'estratos_por_modalidad':dict(Counter(r['tipo_horario'] for r in comparable)),'estratos_pct_finalizada_mayor':sum(r['diferencia_puntos_pct']>0 for r in comparable),'estratos_pct_realizada_mayor':sum(r['diferencia_puntos_pct']<0 for r in comparable),'estratos_pct_igual':sum(r['diferencia_puntos_pct']==0 for r in comparable),'id_en_ambas_encuestas_posteriores':len(set(surveys['Encuesta Express'])&set(surveys['Encuesta Normal'])),'id_en_ambas_encuestas_previas':len(set(surveys['Encuesta Reserva Express'])&set(surveys['Encuesta Reserva Normal IP']))}
    (OUT/'resumen.json').write_text(json.dumps(compact,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(compact,ensure_ascii=False,indent=2))


if __name__=='__main__':
    check()
