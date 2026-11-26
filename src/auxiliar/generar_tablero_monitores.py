"""Local monitor comment explorer; contains names and comments, not published."""
import csv,json
from pathlib import Path
from limpiar_bookeau import ROOT


def generate():
    with (ROOT/'data/oro/texto/comentarios_clasificados.csv').open(newline='',encoding='utf-8') as stream:rows=list(csv.DictReader(stream))
    fields=['id_comentario','id_monitor','monitor','periodo','servicio','modalidad','comentario','etiqueta_automatica','etiqueta_final','origen_etiqueta','etiqueta_revision_ia','justificacion_revision_ia','evidencia_positiva_json','evidencia_negativa_json','temas_json']
    payload=json.dumps([{key:r[key] for key in fields} for r in rows],ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    source=(ROOT/'src/plantillas/tablero_monitores.html').read_text()
    target=ROOT/'exploratorio/tablero_monitores.html'
    target.write_text(source.replace('__DATA__',payload))
    print('Generated:',target,'comments:',len(rows))


if __name__=='__main__':generate()
