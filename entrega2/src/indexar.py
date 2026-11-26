"""Chunking, embeddings y carga del corpus en la base vectorial.

Construye dos colecciones sobre los mismos documentos y con el mismo chunking:
`texto` parte de la capa de texto del PDF y `visual` de la transcripción con visión.
La unidad de chunking es la página (una diapositiva es una idea); solo se parten las
páginas largas, como las del programa del curso.

    python3 src/indexar.py
"""

from collections.abc import Callable

from base_vectorial import COLECCIONES, conectar, reemplazar_fragmentos, resumen
from catalogo import cargar_catalogo
from transcribir import Pagina, leer_transcripcion, paginas_del_documento, texto_del_pdf

MAX_PALABRAS = 200

FUENTE_DE_TEXTO: dict[str, Callable[[Pagina], str]] = {
    'texto': texto_del_pdf,
    'visual': leer_transcripcion,
}


def _lineas_acotadas(texto: str, max_palabras: int) -> list[str]:
    """Líneas del texto; un párrafo de una sola línea más largo que el máximo se divide."""
    lineas = []
    for linea in texto.splitlines():
        palabras = linea.split()
        if len(palabras) <= max_palabras:
            lineas.append(linea)
        else:
            lineas.extend(' '.join(palabras[i:i + max_palabras]) for i in range(0, len(palabras), max_palabras))
    return lineas


def partir_por_lineas(texto: str, max_palabras: int = MAX_PALABRAS) -> list[str]:
    """Parte un texto largo en trozos de hasta `max_palabras` sin cortar líneas.

    Se corta entre líneas, y no cada N palabras, para conservar la indentación del
    código y las filas de las tablas.
    """
    trozos, actual, palabras_actual = [], [], 0
    for linea in _lineas_acotadas(texto, max_palabras):
        palabras = len(linea.split())
        if actual and palabras_actual + palabras > max_palabras:
            trozos.append('\n'.join(actual).strip())
            actual, palabras_actual = [], 0
        actual.append(linea)
        palabras_actual += palabras
    if palabras_actual:
        trozos.append('\n'.join(actual).strip())
    return trozos


def fragmentos_del_documento(paginas: list[Pagina], leer: Callable[[Pagina], str]) -> list[tuple[int, int, str]]:
    return [
        (pagina.numero, indice, trozo)
        for pagina in paginas
        for indice, trozo in enumerate(partir_por_lineas(leer(pagina)))
    ]


def indexar_corpus() -> None:
    documentos = cargar_catalogo()
    with conectar() as conexion:
        for doc in documentos:
            paginas = paginas_del_documento(doc)
            for coleccion in COLECCIONES:
                reemplazar_fragmentos(conexion, doc, coleccion, fragmentos_del_documento(paginas, FUENTE_DE_TEXTO[coleccion]))
        conexion.execute('DELETE FROM documentos WHERE NOT (clave = ANY(%s))', ([doc.clave for doc in documentos],))
        conexion.commit()
        print('colección  vigente  documentos  fragmentos  palabras')
        for coleccion, vigente, n_documentos, n_fragmentos, palabras in resumen(conexion):
            print(f'{coleccion:<10} {"sí" if vigente else "no":<8} {n_documentos:>10}  {n_fragmentos:>10}  {palabras:>8}')


if __name__ == '__main__':
    indexar_corpus()
