"""Produce aggregate CSVs and a standalone interactive HTML dashboard from Gold."""
import csv
import json
import sqlite3
from pathlib import Path
from limpiar_bookeau import ROOT

OUT=ROOT/'docs/entregables'
RESULTS=ROOT/'docs/artifacts/analisis/resultados'


def generate():
    OUT.mkdir(parents=True,exist_ok=True);RESULTS.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(f"file:{ROOT/'data/oro/bookeau.sqlite3'}?mode=ro",uri=True)
    db.row_factory=sqlite3.Row
    def query(sql):return [dict(r) for r in db.execute(sql)]
    demand=query('''SELECT p.periodo_original periodo,s.servicio_original servicio,m.tipo_horario_original modalidad,
        e.estado_analitico estado,e.estado_original estado_original,COUNT(*) n
        FROM hecho_reserva h JOIN dim_periodo p USING(sk_periodo) JOIN dim_servicio s USING(sk_servicio)
        JOIN dim_modalidad m USING(sk_modalidad) JOIN dim_estado e USING(sk_estado)
        GROUP BY p.periodo_original,s.servicio_original,m.tipo_horario_original,e.estado_analitico,e.estado_original''')
    slots=query('''SELECT p.periodo_original periodo,s.servicio_original servicio,m.tipo_horario_original modalidad,
        d.dia_semana_iso dia,t.hora hora,e.grupo_estado grupo,COUNT(*) n FROM hecho_reserva h
        JOIN dim_periodo p USING(sk_periodo) JOIN dim_servicio s USING(sk_servicio) JOIN dim_modalidad m USING(sk_modalidad)
        JOIN dim_estado e USING(sk_estado)
        JOIN dim_fecha d ON d.sk_fecha=h.sk_fecha_inicio JOIN dim_hora t USING(sk_hora_inicio)
        GROUP BY p.periodo_original,s.servicio_original,m.tipo_horario_original,d.dia_semana_iso,t.hora,e.grupo_estado'''.replace('USING(sk_hora_inicio)','ON t.sk_hora=h.sk_hora_inicio'))
    ratings=query('''SELECT p.periodo_original periodo,s.servicio_original servicio,m.tipo_horario_original modalidad,
        COUNT(*) encuestas,COUNT(h.calificacion_ayuda_tutor) calificaciones,
        COALESCE(SUM(h.calificacion_ayuda_tutor),0) suma,
        SUM(CASE WHEN h.calificacion_ayuda_tutor=1 THEN 1 ELSE 0 END) n1,
        SUM(CASE WHEN h.calificacion_ayuda_tutor=2 THEN 1 ELSE 0 END) n2,
        SUM(CASE WHEN h.calificacion_ayuda_tutor=3 THEN 1 ELSE 0 END) n3,
        SUM(CASE WHEN h.calificacion_ayuda_tutor=4 THEN 1 ELSE 0 END) n4,
        SUM(CASE WHEN h.calificacion_ayuda_tutor=5 THEN 1 ELSE 0 END) n5
        FROM hecho_encuesta h JOIN dim_tipo_encuesta t USING(sk_tipo_encuesta)
        JOIN dim_periodo p USING(sk_periodo) JOIN dim_servicio s USING(sk_servicio) JOIN dim_modalidad m USING(sk_modalidad)
        WHERE t.etapa='posterior' GROUP BY p.periodo_original,s.servicio_original,m.tipo_horario_original''')
    texts=query('''SELECT q.texto_pregunta,t.grupo_fuente,COUNT(*) respuestas_textuales
        FROM hecho_respuesta r JOIN dim_pregunta q USING(sk_pregunta)
        JOIN hecho_encuesta e USING(id_encuesta) JOIN dim_tipo_encuesta t USING(sk_tipo_encuesta)
        WHERE q.es_texto_libre=1 GROUP BY q.texto_pregunta,t.grupo_fuente''')
    offer=query('''SELECT p.periodo_original periodo,d.dia_semana_iso dia,t.etiqueta hora,o.cupos_reservados reservados,o.cupos_disponibles disponibles,
        o.asistencias,o.inasistencias,o.cancelaciones,o.en_lista_espera espera,o.reservaron_luego_de_lista luego
        FROM hecho_oferta o JOIN dim_periodo p USING(sk_periodo) JOIN dim_dia_semana d USING(sk_dia_semana)
        JOIN dim_hora t ON t.sk_hora=o.sk_hora_inicio ORDER BY p.periodo_original,d.dia_semana_iso,t.etiqueta''')
    for name,rows in [('reservas.csv',demand),('agenda.csv',slots),('satisfaccion.csv',ratings),('oferta.csv',offer),('texto_disponible.csv',texts)]:
        with (RESULTS/name).open('w',newline='',encoding='utf-8') as stream:
            w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'eventos_reserva':sum(r['n'] for r in demand),'atenciones':sum(r['n'] for r in demand if r['estado']=='Atendida'),'no_asistio_registradas':sum(r['n'] for r in demand if r['estado']=='No asistió'),'encuestas_posteriores_incluidas_R02':sum(r['encuestas'] for r in ratings),'calificaciones_utilizables':sum(r['calificaciones'] for r in ratings),'media_descriptiva':sum(r['suma'] for r in ratings)/sum(r['calificaciones'] for r in ratings)}
    due=summary['atenciones']+summary['no_asistio_registradas']
    summary['tasa_inasistencia_R04']=summary['no_asistio_registradas']/due
    summary['proporcion_cola_R04']=sum(r['n'] for r in slots if r['grupo']=='Cola')/summary['eventos_reserva']
    summary['proporcion_cola_a_reserva']=sum(r['n'] for r in slots if r['grupo']=='Cola a reserva')/summary['eventos_reserva']
    periods_with_cupos={r['periodo'] for r in offer if r['reservados']>0}  # 201620 y 201710 no traen cupos reservados
    with_cupos=[r for r in offer if r['periodo'] in periods_with_cupos]
    summary['capacidad_oferta']=sum(r['disponibles'] for r in offer)
    if with_cupos:
        summary['ocupacion_oferta']=sum(r['reservados'] for r in with_cupos)/sum(r['disponibles'] for r in with_cupos)
        waiting=sum(r['espera'] for r in offer);converted=sum(r['luego'] for r in offer)
        summary['conversion_cola_a_reserva']=converted/(waiting+converted) if waiting+converted else None
    summary['proporcion_calificaciones_bajas']=sum(r['n1']+r['n2']+r['n3'] for r in ratings)/summary['calificaciones_utilizables']
    (RESULTS/'resumen.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    payload=json.dumps({'reservas':demand,'agenda':slots,'satisfaccion':ratings,'oferta':offer},ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    template=(ROOT/'src/plantillas/tablero_bookeau.html').read_text()
    (OUT/'tablero_bookeau.html').write_text(template.replace('__DATA__',payload))
    db.close();print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':generate()
