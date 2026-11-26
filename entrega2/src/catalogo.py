"""Catálogo del corpus: una fila por documento con su semestre, vigencia y nivel.

El catálogo (`data/catalogo_documentos.csv`) es la fuente de las etiquetas que usa
el resto del flujo. Se propone una sola vez a partir de los archivos y después se
corrige a mano: volver a ejecutar este módulo no lo reemplaza, salvo con --regenerar.

    python3 src/catalogo.py [--regenerar]
"""

import argparse
import csv
import re
import subprocess
import unicodedata
import zipfile
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path

import pymupdf

from config import CATALOGO, DIR_HISTORICO, DIR_PAGINAS, DIR_VIGENTE, PERIODO_VIGENTE, RAIZ

EXTENSIONES = {'.pdf', '.pptx'}
DIR_CONVERTIDOS = DIR_PAGINAS / '_convertidos'


@dataclass(frozen=True)
class Documento:
    clave: str
    archivo: str
    titulo: str
    tipo: str
    periodo: str
    vigente: bool
    nivel: int | None
    orden: int | None
    fecha_archivo: str
    paginas_omitidas: tuple[int, ...]

    @property
    def ruta(self) -> Path:
        return RAIZ / self.archivo

    @property
    def etiqueta(self) -> str:
        """Nombre corto con el que se cita el documento en las respuestas."""
        return f'{self.titulo} ({self.periodo})'


def _nfc(texto: str) -> str:
    return unicodedata.normalize('NFC', texto)


def _slug(texto: str) -> str:
    sin_tildes = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', sin_tildes.lower()).strip('-')


def ruta_pdf(doc: Documento) -> Path:
    """PDF del documento; las presentaciones .pptx se convierten una vez con LibreOffice."""
    if doc.ruta.suffix.lower() == '.pdf':
        return doc.ruta
    convertido = DIR_CONVERTIDOS / f'{doc.clave}.pdf'
    if not convertido.exists():
        DIR_CONVERTIDOS.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ['soffice', '--headless', '--convert-to', 'pdf', '--outdir', str(DIR_CONVERTIDOS), str(doc.ruta)],
            check=True, capture_output=True,
        )
        (DIR_CONVERTIDOS / f'{doc.ruta.stem}.pdf').rename(convertido)
    return convertido


def _fecha_archivo(ruta: Path) -> str:
    if ruta.suffix.lower() == '.pptx':
        with zipfile.ZipFile(ruta) as paquete:
            propiedades = paquete.read('docProps/core.xml').decode()
        return re.search(r'<dcterms:modified[^>]*>(\d{4}-\d{2}-\d{2})', propiedades).group(1)
    with pymupdf.open(ruta) as pdf:
        creado = pdf.metadata.get('creationDate') or ''
    coincidencia = re.match(r'D:(\d{4})(\d{2})(\d{2})', creado)
    return '-'.join(coincidencia.groups()) if coincidencia else ''


def _periodo_de_fecha(fecha: str) -> str:
    momento = datetime.strptime(fecha, '%Y-%m-%d')
    return f'{momento.year}-{"10" if momento.month <= 6 else "20"}'


def _nivel_en_portada(ruta: Path) -> int | None:
    if ruta.suffix.lower() == '.pptx':
        with zipfile.ZipFile(ruta) as paquete:
            portada = re.sub(r'<[^>]+>', ' ', paquete.read('ppt/slides/slide1.xml').decode())
    else:
        with pymupdf.open(ruta) as pdf:
            portada = pdf[0].get_text()
    coincidencia = re.search(r'Nivel\s+([1-4])', portada)
    return int(coincidencia.group(1)) if coincidencia else None


def _documento_vigente(ruta: Path) -> Documento:
    nombre = _nfc(ruta.stem)
    presentacion = re.match(r'N(\d)\s*_(\d+)\s*_?\s*(.+)', nombre)
    if presentacion:
        nivel, orden = int(presentacion.group(1)), int(presentacion.group(2))
        titulo = presentacion.group(3).strip().replace('_', ': ')
        clave = f'{PERIODO_VIGENTE}_n{nivel}_{orden:02d}_{_slug(titulo)}'
        tipo = 'presentacion'
    else:
        nivel, orden, titulo = None, None, 'Programa del curso IP'
        clave, tipo = f'{PERIODO_VIGENTE}_programa', 'programa'
    return Documento(
        clave=clave, archivo=_nfc(str(ruta.relative_to(RAIZ))), titulo=titulo, tipo=tipo,
        periodo=PERIODO_VIGENTE, vigente=True, nivel=nivel, orden=orden,
        fecha_archivo=_fecha_archivo(ruta), paginas_omitidas=(),
    )


def _documento_historico(ruta: Path) -> Documento:
    nombre = _nfc(ruta.stem)
    fecha = _fecha_archivo(ruta)
    if 'Programa' in nombre:
        periodo = re.match(r'(\d{4}-\d{2})', nombre).group(1)
        return Documento(
            clave=f'{periodo}_programa', archivo=_nfc(str(ruta.relative_to(RAIZ))),
            titulo='Programa del curso IP', tipo='programa', periodo=periodo, vigente=False,
            nivel=None, orden=None, fecha_archivo=fecha, paginas_omitidas=(),
        )
    partes = re.match(r'(C?\d+)\s*-\s*(.+?)(?:\s*-\s*Copy)?$', nombre)
    numero, titulo = partes.group(1), partes.group(2).strip()
    periodo = _periodo_de_fecha(fecha)
    # La portada de estas presentaciones lleva el nombre y el correo de quien dictó la
    # sección; se omite para no indexar ni enviar datos personales al modelo.
    return Documento(
        clave=f'{periodo}_{_slug(numero)}_{_slug(titulo)}', archivo=_nfc(str(ruta.relative_to(RAIZ))),
        titulo=titulo, tipo='presentacion', periodo=periodo, vigente=False,
        nivel=_nivel_en_portada(ruta), orden=int(numero.lstrip('C')), fecha_archivo=fecha, paginas_omitidas=(1,),
    )


def proponer_catalogo() -> list[Documento]:
    documentos = []
    for carpeta, construir in ((DIR_VIGENTE, _documento_vigente), (DIR_HISTORICO, _documento_historico)):
        for ruta in sorted(carpeta.rglob('*')):
            if ruta.suffix.lower() in EXTENSIONES and not ruta.name.startswith('.'):
                documentos.append(construir(ruta))
    claves = [doc.clave for doc in documentos]
    if len(set(claves)) != len(claves):
        raise ValueError('Hay claves de documento repetidas en el catálogo propuesto.')
    return sorted(documentos, key=lambda doc: doc.clave)


def guardar_catalogo(documentos: list[Documento]) -> None:
    CATALOGO.parent.mkdir(parents=True, exist_ok=True)
    with CATALOGO.open('w', newline='', encoding='utf-8') as salida:
        escritor = csv.DictWriter(salida, fieldnames=[campo.name for campo in fields(Documento)])
        escritor.writeheader()
        for doc in documentos:
            fila = asdict(doc)
            fila['vigente'] = 'si' if doc.vigente else 'no'
            fila['nivel'] = doc.nivel or ''
            fila['orden'] = doc.orden or ''
            fila['paginas_omitidas'] = ' '.join(map(str, doc.paginas_omitidas))
            escritor.writerow(fila)


def cargar_catalogo() -> list[Documento]:
    if not CATALOGO.exists():
        raise FileNotFoundError(f'Falta {CATALOGO}. Ejecuta: python3 src/catalogo.py')
    with CATALOGO.open(encoding='utf-8') as entrada:
        return [
            Documento(
                clave=fila['clave'], archivo=fila['archivo'], titulo=fila['titulo'], tipo=fila['tipo'],
                periodo=fila['periodo'], vigente=fila['vigente'] == 'si',
                nivel=int(fila['nivel']) if fila['nivel'] else None,
                orden=int(fila['orden']) if fila['orden'] else None,
                fecha_archivo=fila['fecha_archivo'],
                paginas_omitidas=tuple(int(p) for p in fila['paginas_omitidas'].split()),
            )
            for fila in csv.DictReader(entrada)
        ]


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumentos.add_argument('--regenerar', action='store_true', help='reemplaza el catálogo, incluidas las correcciones a mano')
    opciones = argumentos.parse_args()
    if CATALOGO.exists() and not opciones.regenerar:
        print(f'{CATALOGO.relative_to(RAIZ)} ya existe ({len(cargar_catalogo())} documentos); se conserva.')
        return
    documentos = proponer_catalogo()
    guardar_catalogo(documentos)
    vigentes = sum(doc.vigente for doc in documentos)
    print(f'{CATALOGO.relative_to(RAIZ)}: {len(documentos)} documentos ({vigentes} vigentes, {len(documentos) - vigentes} históricos)')


if __name__ == '__main__':
    main()
