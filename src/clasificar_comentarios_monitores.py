"""Exploratory Spanish comment classification with reviewable lexical rules.

Not a trained or validated model. Reads included Gold comments and Silver monitor
labels. Unresolved identity discrepancies are kept out of named-monitor totals.
"""
import csv
import hashlib
import json
import random
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from limpiar_bookeau import ROOT

OUT=ROOT/'data/oro/texto'
DOCS=ROOT/'docs/texto'
LABELS=['Positivo','Negativo','Mixto','Sin información suficiente','Por revisar']
PROMPT='Comente aspectos positivos y negativos del tutor y la tutoría. Recuerde que las respuestas van a ser anónimas.'
POSITIVE=[r'\bbien\b',r'\bbuen[oa]?s?\b',r'\bexcelente\b',r'\bincreible\b',r'\bamable\b',r'\bpaciente\b',r'\bclaro\b',r'\bclara\b',r'\bclaridad\b',r'\batento\b',r'\batenta\b',r'\bcomprensiv[oa]\b',r'\bcolaborativ[oa]\b',r'\butil\b',r'\bdispuest[oa]\b',r'\bsolidari[oa]\b',r'\bayud[oae]\b',r'\baprendi\b',r'\bentendi\b',r'\bresolvi[o]?\b',r'\bsolucion[oae]\b',r'\bentender mejor\b',r'\bgran\b',r'\bexplicativ[oa]\b',r'\beficiente\b',r'\btranquil[oa]\b',r'\bdedicad[oa]\b',r'\bpositiv[oa]s?\b']
NEGATIVE=[r'\bmal[oa]?\b',r'\bpesim[oa]\b',r'\bincorrect[oa]\b',r'\bequivocad[oa]\b',r'\bconfus[oa]\b',r'\bgroser[oa]\b',r'\bimpaciente\b',r'\bdesinteres\b',r'\binsuficiente\b',r'\bimpuntual\b',r'\bno (?:me )?(?:ayudo|explico|resolvio|sirvio|entendi)\b',r'\bno (?:supo|sabia|entendia)\b',r'\bpoco tiempo\b',r'\bmuy cort[oa]\b',r'\bfalt[oae] tiempo\b',r'\bperdi (?:mi |el )?tiempo\b',r'\bproblema es\b',r'\bno fue (?:claro|clara|util|bueno|buena)\b',r'\bno (?:fue |era )?(?:tan |muy )?clar[oa]\b']
THEMES={
 'Claridad de explicación':r'explic|clar[oa]|claridad|confus|ejemplo',
 'Resolución de dudas':r'duda|resolver|resolv|solucion|pregunta',
 'Trato y acompañamiento':r'amable|paciente|impaciente|atent|disposicion|groser|comprensiv|ayud|receptiv',
 'Tiempo y duración':r'tiempo|duracion|minutos|cort[oa]|largo',
 'Conocimiento y preparación':r'conocim|dominio|preparad|sabia|supo|sabe|incorrect|equivoc',
 'Puntualidad y disponibilidad':r'puntual|tarde|horario|disponib|espera',
 'Aprendizaje y autonomía':r'aprendi|aprend|entendi|entender|comprend|autonom|por mi cuenta|logica',
 'Conectividad y modalidad':r'internet|conexion|remot|virtual|presencial|tablero',
}
GENERIC={'','n a','na','nada','ninguno','ninguna','no aplica','sin comentarios','ningun comentario','no tengo comentarios','no','ninguna observacion','no se','n s','ns','n r','nr'}


def normalize(value):
    value=''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(c))
    return ' '.join(value.split())


def identity(value):
    return ' '.join(unicodedata.normalize('NFC',value).split()).casefold()


def classify(text):
    normalized=normalize(text)
    words=' '.join(re.findall(r'\w+',normalized))
    if re.fullmatch(r'[:;=]-?[)D]',text.strip(),re.I):
        return 'Positivo',['emoticono favorable'],[],[]
    generic=GENERIC|{'none','todo','todos','ese','x','a','si','nada en especifico','nada en especial'}
    if words in generic or not re.search(r'[a-z]',words) or (len(words)<=2 and words!='ok') or (' ' not in words and not re.search(r'[aeiou]',words)):
        return 'Sin información suficiente',[],[],[]
    if re.match(r'^no enti[end]+',normalized) and not re.search(r'tutor|monitor|sesion|tutoria|ayud|explic|sirvi',normalized):
        return 'Sin información suficiente',[],[],[]
    positive,negative=[],[]
    # Suppress prior student difficulties, rather than treating them as monitor criticism.
    analysis=normalized
    analysis=re.sub(r'(?:lo |algo |conceptos? |temas? |parte .*? |ejercicio .*? )?que (?:yo )?no (?:entendia|entendi|sabia|tenia (?:muy )?clar[oa]s?)', ' dificultad previa del estudiante ',analysis)
    analysis=re.sub(r'(?:siempre |y si |si )no entendia[^.!?;]*?(?=(?:volvi|explic|ense|ayud))',' dificultad previa ',analysis)
    analysis=re.sub(r'cuando le decia que no entendia',' dificultad previa ',analysis)
    if re.search(r'llam[oae][^.!?]*?(?:superior|otro tutor)',analysis) and re.search(r'buen|excelente|positiv',analysis):
        analysis=re.sub(r'no supo\b','busco apoyo',analysis)
    extra_positive=[r'\baclar[oae]\b',r'\baclare\b',r'\bclaramente\b',r'\bpaciencia\b',r'\bcalma\b',r'\butiles\b',r'\breceptiv[oa]\b',r'\bcolaborador[a]?\b',r'\bquerid[oa]\b',r'\bme sirvio\b',r'\bsabe\b',r'\bconoce\b',r'\bconocimiento\b',r'\bexplico\b',r'\bentiende\b',r'\bentendio\b',r'\blogro\b',r'\bse preocupa\b',r'\bse preocupo\b',r'\bse asegura\b',r'\bse esforzo\b',r'\blo intenta\b',r'\bintencion de ayudar\w*',r'\bprofundiza\b',r'\bfacil de entender\b',r'\brelajad[oa]\b',r'\bme gusto\b',r'\bme agrado\b',r'\blogre\b',r'\bayudaron\b',r'\bprogresar\b',r'\binteres en\b',r'\bse dio cuenta\b',r'\bsuper\b',r'\bok\b']
    extra_negative=[r'\bllego tarde\b',r'\bno llego\b',r'\bno (?:sab|sabe) explicarse\b',r'\bno (?:pude|pudimos|logro|logramos) (?:resolver|solucionar|ayudar\w*|arreglar)\b',r'\bno (?:supo|sabia)\b',r'\bno manejaba\b',r'\bfalta (?:de |darse |explicar|claridad|atencion)',r'\bdeberia\b',r'\bfastidio\b',r'\bno (?:te )?inspira\b',r'\bno (?:me )?gusta\b',r'\bfallan\b',r'\bproblemas para (?:poder )?escuch',r'\bno permitia\b',r'\bno pude\b',r'\bno se (?:comunicaba|hizo)\b',r'\btarde[^.!?;]*?(?:entrar|acceder)\b']
    def negated(match):
        prefix=re.split(r'[.!?;,:]',analysis[max(0,match.start()-70):match.start()])[-1]
        prefix=re.split(r'\b(?:pero|aunque|sin embargo|y)\b',prefix)[-1]
        return bool(re.search(r'\b(?:no|nunca|sin|poco|ni)\b(?:\s+\w+){0,4}\s*$',prefix))
    for pattern in POSITIVE+extra_positive:
        for match in re.finditer(pattern,analysis):
            if negated(match):
                negative.append('valoracion favorable negada: '+match.group());continue
            before=analysis[max(0,match.start()-75):match.start()]
            # A desirable outcome in an unachieved goal is not an achieved benefit.
            if match.group() in {'bien','claro','clara'} and re.search(r'\b(?:para|permitia|permitiera)\b[^.!?;]*$',before):continue
            positive.append(match.group())
    for pattern in NEGATIVE+extra_negative:
        for match in re.finditer(pattern,analysis):
            token=match.group()
            if token=='no entendia':continue
            before=analysis[max(0,match.start()-70):match.start()]
            after=analysis[match.end():match.end()+65]
            if token.startswith('no sabia') and re.search(r'\b(?:yo|que)\s*$',before):continue
            if token in {'mal','malo','mala','confuso','confusa'}:
                if re.search(r'(?:\b(?:yo|mis|mi|tenia|tenian|tonto|escribir)\b|conceptos)[^.!?;]*$',before) or re.match(r'\s+(?:en (?:el|mi) laboratorio|(?:lab\w*|ejercicio|problema)\b)',after):continue
            if not token.startswith('no ') and negated(match):continue
            negative.append(token)
    themes=[name for name,pattern in THEMES.items() if re.search(pattern,normalized)]
    # Unclear subject in a contrast clause can change the polarity interpretation.
    if re.search(r'\b(?:aunque|pero)\b[^.!?;]*\bno entendia\b',normalized) and not any(not n.startswith('valoracion favorable negada:') for n in negative):
        return 'Por revisar',sorted(set(positive)),['sujeto ambiguo de no entendia'],themes
    label='Mixto' if positive and negative else 'Positivo' if positive else 'Negativo' if negative else 'Por revisar'
    return label,sorted(set(positive)),sorted(set(negative)),themes


def read(path):
    with path.open(newline='',encoding='utf-8-sig') as stream:return list(csv.DictReader(stream))


def write(path,rows,fields=None):
    if not rows and not fields:return
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields or list(rows[0]));writer.writeheader();writer.writerows(rows)


def run():
    OUT.mkdir(parents=True,exist_ok=True);DOCS.mkdir(parents=True,exist_ok=True)
    reservation_monitors={r['id_reserva']:r['prestador_servicio'] for r in read(ROOT/'data/plata/reservas.csv')}
    surveys={}
    for filename in ['encuesta_satisfaccion_express','encuesta_satisfaccion_normal']:
        for r in read(ROOT/'data/plata'/f'{filename}.csv'):
            if r['incluir_encuesta_en_analisis']=='true':surveys[filename+':'+r['id_reserva']]=r
    db=sqlite3.connect(f"file:{ROOT/'data/oro/bookeau.sqlite3'}?mode=ro",uri=True);db.row_factory=sqlite3.Row
    comments=list(db.execute('''SELECT e.id_encuesta,e.id_reserva,p.periodo_original periodo,s.servicio_original servicio,m.tipo_horario_original modalidad,r.valor_original comentario
       FROM hecho_respuesta r JOIN dim_pregunta q USING(sk_pregunta) JOIN hecho_encuesta e USING(id_encuesta)
       JOIN dim_periodo p ON p.sk_periodo=e.sk_periodo JOIN dim_servicio s ON s.sk_servicio=e.sk_servicio
       JOIN dim_modalidad m ON m.sk_modalidad=e.sk_modalidad WHERE q.texto_pregunta=?''',(PROMPT,)))
    db.close()
    manual_path=DOCS/'etiquetas_manuales.csv'
    manual_rows=read(manual_path) if manual_path.exists() else []
    manual={}
    for r in manual_rows:
        value=r.get('etiqueta_manual','').strip()
        if not value:continue
        if value not in LABELS:raise ValueError('Unknown manual label')
        if r['id_comentario'] in manual:raise ValueError('Repeated manual annotation')
        manual[r['id_comentario']]=value
    ia_path=DOCS/'etiquetas_revisadas_ia.csv'
    ia={}
    for r in read(ia_path) if ia_path.exists() else []:
        if r['etiqueta_revision_ia'] not in LABELS:raise ValueError('Unknown IA label')
        if r['id_comentario'] in ia:raise ValueError('Repeated IA annotation')
        ia[r['id_comentario']]=r
    monitor_names=defaultdict(Counter)
    rows=[]
    for comment in comments:
        row=dict(comment);source=surveys[row['id_encuesta']]
        a=source['prestador_servicio'];b=reservation_monitors[row['id_reserva']]
        na,nb=identity(a),identity(b)
        if na and nb and na==nb:
            monitor_id='monitor_'+hashlib.sha256(na.encode()).hexdigest()[:16]
            monitor_names[monitor_id][' '.join(unicodedata.normalize('NFC',a).split())]+=1
            monitor_status='Coincide entre encuesta y reserva'
        elif not na and not nb:
            monitor_id='sin_monitor_confirmado';monitor_status='Sin monitor en ambas fuentes'
        elif not na or not nb:
            monitor_id='sin_monitor_confirmado';monitor_status='Monitor presente en una sola fuente; revisar'
        else:
            monitor_id='sin_monitor_confirmado';monitor_status='Diferencia entre encuesta y reserva; revisar'
        identifier=hashlib.sha256((row['id_encuesta']+'|'+PROMPT).encode()).hexdigest()[:24]
        label,positive,negative,themes=classify(row['comentario'])
        row.update(id_comentario=identifier,id_monitor=monitor_id,monitor_encuesta_original=a,monitor_reserva_original=b,estado_identificacion_monitor=monitor_status,etiqueta_automatica=label,etiqueta_final=manual.get(identifier,label),origen_etiqueta='Manual' if identifier in manual else 'Reglas exploratorias sin validar',evidencia_positiva_json=json.dumps(positive,ensure_ascii=False),evidencia_negativa_json=json.dumps(negative,ensure_ascii=False),temas_json=json.dumps(themes,ensure_ascii=False))
        if identifier in ia:
            row['etiqueta_revision_ia']=ia[identifier]['etiqueta_revision_ia']
            row['justificacion_revision_ia']=ia[identifier]['justificacion']
            if identifier not in manual:
                row['etiqueta_final']=row['etiqueta_revision_ia']
                row['origen_etiqueta']='Revisión IA'
        else:
            row['etiqueta_revision_ia']=''
            row['justificacion_revision_ia']=''
        rows.append(row)
    names={identifier:variants.most_common(1)[0][0] for identifier,variants in monitor_names.items()}
    names['sin_monitor_confirmado']='Sin monitor confirmado · revisión de identidad'
    for row in rows:row['monitor']=names[row['id_monitor']]
    write(OUT/'comentarios_clasificados.csv',rows)
    write(OUT/'monitores.csv',[{'id_monitor':identifier,'nombre_mostrado':name,'tipo_clave':'Etiqueta normalizada, no ID certificado de persona' if identifier!='sin_monitor_confirmado' else 'No atribuir a una persona'} for identifier,name in sorted(names.items())])
    aggregations=defaultdict(Counter)
    theme_aggregations=Counter()
    for r in rows:
        key=(r['id_monitor'],r['periodo'],r['servicio'],r['modalidad'])
        aggregations[key][r['etiqueta_final']]+=1
        for theme in json.loads(r['temas_json']):theme_aggregations[(*key,theme)]+=1
    aggregates=[{'id_monitor':key[0],'monitor':names[key[0]],'periodo':key[1],'servicio':key[2],'modalidad':key[3],'comentarios_exportados':sum(counts.values()),**{label:counts[label] for label in LABELS}} for key,counts in sorted(aggregations.items())]
    write(OUT/'resumen_monitores_segmentos.csv',aggregates)
    theme_rows=[{'id_monitor':key[0],'monitor':names[key[0]],'periodo':key[1],'servicio':key[2],'modalidad':key[3],'tema':key[4],'comentarios_que_mencionan_tema':count} for key,count in sorted(theme_aggregations.items())]
    write(OUT/'temas_monitores.csv',theme_rows)
    if not manual_path.exists():
        generator=random.Random(42);sample=[]
        for label in LABELS:
            candidates=[r for r in rows if r['etiqueta_automatica']==label]
            sample.extend(generator.sample(candidates,min(30,len(candidates))))
        write(manual_path,[{'id_comentario':r['id_comentario'],'comentario':r['comentario'],'etiqueta_automatica':r['etiqueta_automatica'],'etiqueta_manual':'','observacion_revisor':''} for r in sample])
    labeled=[r for r in rows if r['id_comentario'] in manual]
    confusion=Counter((manual[r['id_comentario']],r['etiqueta_automatica']) for r in labeled)
    validation={'comentarios_etiquetados_manualmente':len(labeled),'etiquetas_manuales_sin_comentario_actual':len(set(manual)-{r['id_comentario'] for r in rows}),'estado':'Sin evaluación humana; precisión desconocida' if not labeled else 'Evaluación sobre muestra revisada, no estimación poblacional ni evaluación independiente','coincidencia_en_muestra':sum(a==b for (a,b),n in confusion.items() for _ in range(n))/len(labeled) if labeled else None,'matriz_confusion':[{'manual':a,'automatico':b,'n':n} for (a,b),n in sorted(confusion.items())]}
    validation['comentarios_revisados_ia']=sum(r['id_comentario'] in ia for r in rows)
    validation['evaluacion_ia']='docs/texto/validacion_ia/resultados.json'
    (DOCS/'evaluacion_clasificador.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
    summary={'comentarios_validos_exportados':len(rows),'etiquetas_automaticas':dict(Counter(r['etiqueta_automatica'] for r in rows)),'etiquetas_finales':dict(Counter(r['etiqueta_final'] for r in rows)),'comentarios_sin_monitor_confirmado':sum(r['id_monitor']=='sin_monitor_confirmado' for r in rows),'etiquetas_monitor_con_comentarios_atribuidos':len(monitor_names),'identificacion_monitor':dict(Counter(r['estado_identificacion_monitor'] for r in rows)),'comentarios_revision_manual':len(labeled)}
    summary['comentarios_revision_ia']=validation['comentarios_revisados_ia']
    (DOCS/'resumen.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return rows,aggregates,theme_rows


if __name__=='__main__':run()
