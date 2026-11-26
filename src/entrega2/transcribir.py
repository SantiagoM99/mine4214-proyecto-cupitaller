"""Ingesta visual: cada página se renderiza como imagen y un modelo con visión la transcribe.

Las presentaciones del curso llevan el código como capturas de pantalla y el programa
2020-20 no tiene capa de texto, así que la extracción de texto del PDF pierde ese
contenido. La transcripción se hace una vez por página y queda en disco
(`data/plata/documentos/transcripciones/<clave>/pNNN.md`); volver a ejecutar solo procesa lo que falta.

    python3 src/entrega2/transcribir.py [--trabajadores 6]
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import openai
import pymupdf

from catalogo import Documento, cargar_catalogo, ruta_pdf
from config import DIR_PAGINAS, DIR_TRANSCRIPCIONES
from llm import CACHE_EXPLICITA, cliente, generar, imagen_como_entrada

LADO_MAYOR_PX = 1600
SIN_CONTENIDO = 'SIN_CONTENIDO'
REGISTRO_USO = DIR_TRANSCRIPCIONES / 'uso.jsonl'

INSTRUCCIONES = f"""Transcribes a Markdown una página de un documento del curso Introducción a la Programación (Universidad de los Andes).

Reglas:
- Si la página tiene título, la primera línea es `# ` seguido del título.
- Copia todo el texto visible tal como aparece, en orden de lectura.
- Copia el código exactamente, con su indentación, en bloques ```python. Incluye el código y las salidas de consola que aparecen dentro de imágenes o capturas de pantalla.
- Escribe las tablas como tablas Markdown.
- Por cada figura, diagrama o gráfica que aporte contenido, escribe una línea que empiece por `[Figura]` y diga qué muestra.
- Omite logos, números de página y pies de página institucionales.
- No expliques ni agregues contenido que no esté en la página.
- Si la página no tiene contenido propio (por ejemplo, solo un logo), responde únicamente {SIN_CONTENIDO}."""


@dataclass(frozen=True)
class Pagina:
    documento: Documento
    numero: int

    @property
    def imagen(self) -> Path:
        return DIR_PAGINAS / self.documento.clave / f'p{self.numero:03d}.png'

    @property
    def transcripcion(self) -> Path:
        return DIR_TRANSCRIPCIONES / self.documento.clave / f'p{self.numero:03d}.md'


def paginas_del_documento(doc: Documento) -> list[Pagina]:
    with pymupdf.open(ruta_pdf(doc)) as pdf:
        total = len(pdf)
    return [Pagina(doc, numero) for numero in range(1, total + 1) if numero not in doc.paginas_omitidas]


def texto_del_pdf(pagina: Pagina) -> str:
    """Capa de texto de la página, tal como la entrega el PDF (sin visión)."""
    with pymupdf.open(ruta_pdf(pagina.documento)) as pdf:
        return pdf[pagina.numero - 1].get_text('text', sort=True).strip()


def renderizar(pagina: Pagina) -> Path:
    if not pagina.imagen.exists():
        pagina.imagen.parent.mkdir(parents=True, exist_ok=True)
        with pymupdf.open(ruta_pdf(pagina.documento)) as pdf:
            hoja = pdf[pagina.numero - 1]
            escala = LADO_MAYOR_PX / max(hoja.rect.width, hoja.rect.height)
            hoja.get_pixmap(matrix=pymupdf.Matrix(escala, escala)).save(pagina.imagen)
    return pagina.imagen


def leer_transcripcion(pagina: Pagina) -> str:
    """Transcripción guardada de la página; cadena vacía si la página no tiene contenido."""
    texto = pagina.transcripcion.read_text(encoding='utf-8').strip()
    return '' if texto == SIN_CONTENIDO else texto


def _pedir_transcripcion(api, pagina: Pagina, capa_de_texto: str):
    pista = (
        'Texto extraído automáticamente del PDF. Puede estar incompleto o desordenado; '
        f'úsalo solo para confirmar la ortografía de lo que ves:\n{capa_de_texto}'
        if capa_de_texto else 'El PDF no tiene texto extraíble para esta página.'
    )
    return generar(api, INSTRUCCIONES, [{'role': 'user', 'content': [
        {'type': 'input_text', 'text': pista},
        imagen_como_entrada(renderizar(pagina)),
    ]}], **CACHE_EXPLICITA)


def _transcribir(api, pagina: Pagina) -> dict:
    """Transcribe una página y devuelve su registro de consumo.

    El filtro de contenido del proveedor rechaza a veces una diapositiva inofensiva.
    En ese caso la página conserva la capa de texto del PDF, para que no desaparezca
    del corpus, y el registro lo indica en `metodo`.
    """
    capa_de_texto = texto_del_pdf(pagina)
    registro = {'clave': pagina.documento.clave, 'pagina': pagina.numero}
    try:
        respuesta = _pedir_transcripcion(api, pagina, capa_de_texto)
        texto, registro = respuesta.texto.strip(), {**registro, 'metodo': 'vision', **respuesta.uso}
    except openai.BadRequestError:
        texto, registro = capa_de_texto or SIN_CONTENIDO, {**registro, 'metodo': 'capa_de_texto'}
    pagina.transcripcion.parent.mkdir(parents=True, exist_ok=True)
    pagina.transcripcion.write_text(texto + '\n', encoding='utf-8')
    return registro


def transcribir_corpus(trabajadores: int) -> None:
    pendientes = [
        pagina
        for doc in cargar_catalogo()
        for pagina in paginas_del_documento(doc)
        if not pagina.transcripcion.exists()
    ]
    if not pendientes:
        print('Todas las páginas ya están transcritas.')
        return
    api = cliente()
    DIR_TRANSCRIPCIONES.mkdir(parents=True, exist_ok=True)
    inicio = time.perf_counter()
    sin_vision = 0
    with ThreadPoolExecutor(trabajadores) as grupo, REGISTRO_USO.open('a', encoding='utf-8') as salida:
        tareas = [grupo.submit(_transcribir, api, pagina) for pagina in pendientes]
        for hechas, tarea in enumerate(as_completed(tareas), start=1):
            registro = tarea.result()
            sin_vision += registro['metodo'] != 'vision'
            salida.write(json.dumps(registro, ensure_ascii=False) + '\n')
            salida.flush()
            if hechas % 100 == 0 or hechas == len(pendientes):
                print(f'  {hechas}/{len(pendientes)} páginas transcritas')
    print(f'{len(pendientes)} páginas en {time.perf_counter() - inicio:.0f} s con {trabajadores} llamadas simultáneas; '
          f'{sin_vision} quedaron con la capa de texto por rechazo del proveedor')


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumentos.add_argument('--trabajadores', type=int, default=6, help='llamadas simultáneas al modelo')
    transcribir_corpus(argumentos.parse_args().trabajadores)


if __name__ == '__main__':
    main()
