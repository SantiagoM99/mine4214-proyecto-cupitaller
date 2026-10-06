"""Render entregables/informe_entrega_1.md to PDF through headless Chrome (needs the `markdown` package)."""
import base64
import re
import subprocess
import tempfile
from pathlib import Path
import markdown
from limpiar_bookeau import ROOT

SOURCE=ROOT/'entregables/informe_entrega_1.md'
TARGET=ROOT/'entregables/informe_entrega_1.pdf'
CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
CSS='''
@page{size:Letter;margin:18mm 16mm}
body{font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;font-size:10pt;line-height:1.45;color:#17243a}
h1{font-size:19pt;margin:0 0 6pt}h2{font-size:14pt;margin:18pt 0 6pt;padding-bottom:3pt;border-bottom:1px solid #c9d3df;page-break-after:avoid}
h3{font-size:11.5pt;margin:12pt 0 4pt;page-break-after:avoid}
table{border-collapse:collapse;width:100%;margin:6pt 0 10pt;font-size:8.6pt;page-break-inside:avoid}
th,td{border:1px solid #d5dde7;padding:3pt 5pt;vertical-align:top}th{background:#eef2f7;text-align:left}
img{max-width:100%;display:block;margin:6pt auto 10pt;page-break-inside:avoid}
pre{background:#f4f6f9;padding:8pt;font-size:8pt;line-height:1.3;white-space:pre-wrap;page-break-inside:avoid}
code{font-size:8.8pt}blockquote{border-left:3px solid #d19627;background:#fff9ec;margin:6pt 0;padding:4pt 10pt}
hr{border:0;border-top:1px solid #c9d3df}
'''


def inline_images(html):
    def embed(match):
        path=(SOURCE.parent/match.group(1)).resolve()
        return f'src="data:image/png;base64,{base64.b64encode(path.read_bytes()).decode()}"'
    return re.sub(r'src="([^"]+\.png)"',embed,html)


def generate():
    body=markdown.markdown(SOURCE.read_text(encoding='utf-8'),extensions=['tables','fenced_code'])
    page=f'<!doctype html><html lang="es"><meta charset="utf-8"><style>{CSS}</style><body>{inline_images(body)}</body></html>'
    with tempfile.NamedTemporaryFile('w',suffix='.html',delete=False,encoding='utf-8') as stream:
        stream.write(page)
    subprocess.run([CHROME,'--headless=new','--disable-gpu','--no-pdf-header-footer',
                    f'--print-to-pdf={TARGET}',f'file://{stream.name}'],check=True,capture_output=True)
    Path(stream.name).unlink()
    print('Generado:',TARGET)


if __name__=='__main__':generate()
