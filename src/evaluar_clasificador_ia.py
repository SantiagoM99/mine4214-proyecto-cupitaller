"""Compare frozen predictions against explicit AI reference annotations.

This evaluates agreement with this assistant, not human ground truth. Development
and held-out results stay separate. No model is adjusted by this script.
"""
import csv
import json
from collections import Counter
from clasificar_comentarios_monitores import DOCS, LABELS, read, write


def metrics(rows, predictions):
    confusion=Counter((r['etiqueta_revision_ia'],predictions[r['id_comentario']]) for r in rows)
    per_class=[]
    for label in LABELS:
        tp=confusion[label,label]
        reference=sum(n for (a,b),n in confusion.items() if a==label)
        predicted=sum(n for (a,b),n in confusion.items() if b==label)
        precision=tp/predicted if predicted else 0
        recall=tp/reference if reference else 0
        per_class.append({'etiqueta':label,'referencia_ia':reference,'predicciones':predicted,
                          'precision_respecto_ia':precision,'recobrado_respecto_ia':recall,
                          'f1_respecto_ia':2*precision*recall/(precision+recall) if precision+recall else 0})
    matches=sum(n for (a,b),n in confusion.items() if a==b)
    return {'n':len(rows),'coincidencias':matches,'coincidencia_con_revision_ia':matches/len(rows),
            'macro_f1_respecto_ia':sum(r['f1_respecto_ia'] for r in per_class)/len(LABELS),
            'por_clase':per_class,
            'matriz_confusion':[{'referencia_ia':a,'prediccion':b,'n':confusion[a,b]} for a in LABELS for b in LABELS]}


def run():
    folder=DOCS/'validacion_ia'
    annotations=read(DOCS/'etiquetas_revisadas_ia.csv')
    if len({r['id_comentario'] for r in annotations})!=len(annotations):raise ValueError('Duplicate annotation')
    results={'referencia':'Revisión semántica IA por el mismo asistente que desarrolló las reglas; no evaluación humana independiente',
             'diseno':'Muestras estratificadas por predicción v1; no estimación de exactitud poblacional. Textos de evaluación separados de desarrollo.',
             'conclusion':'La versión v2 no es suficientemente fiable para conclusiones de desempeño por monitor.'}
    errors=[]
    for version in ['v1','v2']:
        predictions={r['id_comentario']:r['etiqueta_automatica'] for r in read(folder/f'predicciones_{version}.csv')}
        results[version]={}
        for partition in ['desarrollo','evaluacion_reservada']:
            rows=[r for r in annotations if r['particion']==partition]
            results[version][partition]=metrics(rows,predictions)
            for r in rows:
                if predictions[r['id_comentario']]!=r['etiqueta_revision_ia']:
                    errors.append({'version':version,'particion':partition,'id_comentario':r['id_comentario'],
                                   'comentario':r['comentario'],'prediccion':predictions[r['id_comentario']],
                                   'referencia_ia':r['etiqueta_revision_ia'],'justificacion':r['justificacion']})
    (folder/'resultados.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    write(folder/'desacuerdos.csv',errors)
    print(json.dumps({v:{p:(m['coincidencias'],m['n']) for p,m in results[v].items()} for v in ['v1','v2']}))
    return results


if __name__=='__main__':run()
