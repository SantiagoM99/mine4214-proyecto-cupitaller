"""Dibuja el modelo dimensional de la Entrega 1 como diagrama de tablas para el póster.

    python3 src/auxiliar/e2_modelo_dimensional.py

Escribe artifacts/entrega2/poster/modelo_dimensional.svg. El contenido de cada tabla se
declara aquí, en el orden en que se quiere leer, y se comprueba contra el DDL del
modelo (sql/e2_bodega_modelo_gold.sql): si una columna del DDL no aparece en el dibujo,
o una relación del dibujo no existe en el DDL, el script se detiene.

Las tablas van en cuatro columnas: la reserva (con la oferta y el día de la semana
debajo), las siete dimensiones que comparten la reserva y la encuesta, la encuesta y
la respuesta. Cada relación sale de la fila de la PK (una barra: lado uno) y llega a
la fila de la FK (pata de gallo: lado muchos) por un canal entre columnas, en tramos
horizontales y verticales; si la FK admite nulos en el DDL, el lado uno lleva además
un círculo (cero o uno). En cada canal el orden de los carriles es el que menos
cruces produce entre todas sus permutaciones.
"""

import itertools
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from functools import cache
from html import escape
from pathlib import Path

from PIL import ImageFont

import sys

# Código auxiliar (informe y póster): usa los módulos del núcleo de la Entrega 2.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'entrega2'))

from config import ARTIFACTS, GOLD_ENTREGA1, RAIZ

DDL = RAIZ / 'sql' / 'e2_bodega_modelo_gold.sql'
DESTINO = ARTIFACTS / 'poster' / 'modelo_dimensional.svg'
# Las filas se cuentan en el oro de la Entrega 1 y no en la copia de la bodega, que no
# guarda las 25.256 respuestas de texto libre.
ORO = GOLD_ENTREGA1

# Columnas de trazabilidad que todas las tablas de hechos tienen; se resumen en una línea.
LINAJE = {'archivo_origen', 'hoja_origen', 'fila_excel', 'banderas_calidad_json', 'diferencias_con_reserva_json'}
LINEA_DE_LINAJE = ('+', 'linaje y banderas de calidad')
DIVISOR = ('—', '')
# Rótulos de sección bajo el divisor: separan las medidas de los atributos degenerados
# (columnas descriptivas que viven en el hecho porque no tienen dimensión propia).
MEDIDAS = ('§', 'medidas')
DEGENERADOS = ('§', 'atributos degenerados')

ALTO_DE_LINEA = 6.9
ALTO_CABECERA_HECHO = 16
ALTO_CABECERA_DIMENSION = 11
TAMANO_COLUMNA = 5.6
SANGRIA_COLUMNA = 18
# Por encima de las cajas pasa la llave de la encuesta a la reserva.
MARGEN_SUPERIOR = 8
SEPARACION_CENTRAL = 4
SEPARACION_LATERAL = 12
PASO_DE_CARRIL = 3.2
# Tramo junto al borde de una caja reservado a la barra o la pata de gallo; los carriles empiezan después.
ZONA_DE_MARCA = 6.5
# Cada caja se dimensiona según su línea más larga, medida con la fuente con que se
# imprime el póster. Sin ella se usa el ancho medio de un carácter de Helvetica, que
# sobrestima hasta un 15 %.
FUENTE = Path('/System/Library/Fonts/HelveticaNeue.ttc')
ANCHO_DE_CARACTER = 0.53
TINTA = '#1c1c1c'
GRIS = '#6e6e6e'
LINEA_RELACION = '#3a3a3a'

# (etiqueta, texto). La etiqueta va en gris a la izquierda: PK, FK, «+» para el linaje.
# Las FK de la reserva y la encuesta siguen el orden de la columna central.
HECHOS = {
    'hecho_reserva': ('una reserva', [
        ('PK', 'id_reserva'), ('FK', 'sk_fecha_inicio'), ('FK', 'sk_fecha_fin'), ('FK', 'sk_fecha_llegada'),
        ('FK', 'sk_servicio'), ('FK', 'sk_modalidad'), ('FK', 'sk_estado'), ('FK', 'sk_programa'),
        ('FK', 'sk_periodo'), ('FK', 'sk_hora_inicio'), DIVISOR,
        MEDIDAS, ('', 'evento_reserva = 1'), ('', 'duracion_programada_minutos'), DIVISOR,
        DEGENERADOS, ('', 'fecha_inicio · fecha_fin (con hora)'), ('', 'fecha_llegada (con hora)'), ('', 'es_prioritaria'),
        LINEA_DE_LINAJE,
    ]),
    'hecho_oferta': ('período × día × hora', [
        ('PK FK', 'sk_periodo'), ('PK FK', 'sk_hora_inicio'), ('PK FK', 'sk_dia_semana'), DIVISOR,
        MEDIDAS, ('', 'cupos_disponibles'), ('', 'cupos_reservados'), ('', 'asistencias'), ('', 'cancelaciones'),
        ('', 'inasistencias'), ('', 'en_lista_espera'), ('', 'reservaron_luego_de_lista'), LINEA_DE_LINAJE,
    ]),
    'hecho_encuesta': ('una encuesta respondida', [
        ('PK', 'id_encuesta'), ('FK', 'id_reserva'), ('FK', 'sk_tipo_encuesta'), ('FK', 'sk_fecha_inicio'),
        ('FK', 'sk_servicio'), ('FK', 'sk_modalidad'), ('FK', 'sk_estado'), ('FK', 'sk_programa'),
        ('FK', 'sk_periodo'), ('FK', 'sk_hora_inicio'), DIVISOR,
        MEDIDAS, ('', 'respuesta_encuesta = 1'), ('', 'calificacion_ayuda_tutor'), LINEA_DE_LINAJE,
    ]),
    'hecho_respuesta': ('una pregunta respondida', [
        ('PK FK', 'id_encuesta'), ('PK FK', 'sk_pregunta'), DIVISOR,
        MEDIDAS, ('', 'respuesta_item = 1'), ('', 'valor_numerico'), DIVISOR,
        DEGENERADOS, ('', 'valor_original'),
    ]),
}

DIMENSIONES = {
    'dim_dia_semana': [('PK', 'sk_dia_semana'), ('', 'dia_semana_iso'), ('', 'nombre_dia'), ('', 'es_fin_de_semana')],
    'dim_hora': [('PK', 'sk_hora'), ('', 'hora › minuto'), ('', 'etiqueta'), ('', 'franja')],
    'dim_periodo': [('PK', 'sk_periodo'), ('', 'periodo_original'), ('', '› tipo_periodo'), ('', 'anio_codigo'), ('', 'sufijo_original')],
    'dim_fecha': [('PK', 'sk_fecha'), ('', 'fecha › mes › anio'), ('', 'dia · dia_semana_iso'), ('', 'nombre_dia · nombre_mes'), ('', 'es_fin_de_semana')],
    'dim_tipo_encuesta': [('PK', 'sk_tipo_encuesta'), ('', 'grupo_fuente'), ('', 'etapa')],
    'dim_programa': [('PK', 'sk_programa'), ('', 'programa_normalizado')],
    'dim_servicio': [('PK', 'sk_servicio'), ('', 'codigo_servicio'), ('', 'servicio_original')],
    'dim_modalidad': [('PK', 'sk_modalidad'), ('', 'tipo_horario_original'), ('', 'categoria_original')],
    'dim_estado': [('PK', 'sk_estado'), ('', 'estado_original'), ('', '› estado_analitico'), ('', '› grupo_estado')],
    'dim_pregunta': [('PK', 'sk_pregunta'), ('', 'texto_pregunta'), ('', 'columna_plata'), ('', 'es_texto_libre'), ('', 'es_calificacion_tutor')],
}

COLUMNAS = [
    ['hecho_reserva', 'hecho_oferta', 'dim_dia_semana'],
    ['dim_fecha', 'dim_servicio', 'dim_modalidad', 'dim_estado', 'dim_programa', 'dim_periodo', 'dim_hora'],
    ['hecho_encuesta', 'dim_tipo_encuesta'],
    ['hecho_respuesta', 'dim_pregunta'],
]
# Una dimensión en la misma columna que el único hecho que la usa se conecta por el canal de este lado.
LADO_PROPIO = {'dim_dia_semana': 'izquierda', 'dim_tipo_encuesta': 'derecha', 'dim_pregunta': 'derecha'}
# Llaves que apuntan a otra tabla de hechos: (hecho, columna) -> (hecho destino, columna destino).
ENLACES_ENTRE_HECHOS = {
    ('hecho_encuesta', 'id_reserva'): ('hecho_reserva', 'id_reserva'),
    ('hecho_respuesta', 'id_encuesta'): ('hecho_encuesta', 'id_encuesta'),
}
TOPE = 'tope'


@dataclass
class Caja:
    tabla: str
    x: float
    y: float
    ancho: float
    alto: float

    @property
    def derecha(self) -> float:
        return self.x + self.ancho

    @property
    def abajo(self) -> float:
        return self.y + self.alto


@dataclass
class Fila:
    etiqueta: str
    contenido: str
    base: float

    @property
    def centro(self) -> float:
        return self.base - TAMANO_COLUMNA * 0.34


@dataclass
class Relacion:
    """Una FK: la tabla del lado muchos apunta a la del lado uno."""
    muchos: str
    columna_muchos: str
    uno: str
    columna_uno: str
    opcional: bool


@dataclass
class Pin:
    lado: str  # borde del canal: 'izquierda' o 'derecha'
    y: float
    marca: str | None  # 'uno', 'cero_o_uno', 'muchos', o None si el trazo sigue fuera del canal


@dataclass
class Red:
    pines: list[Pin] = field(default_factory=list)
    punteada: bool = False

    @property
    def extremos(self) -> tuple[float, float]:
        ys = [pin.y for pin in self.pines]
        return min(ys), max(ys)


@dataclass
class Canal:
    x0: float = 0
    x1: float = 0
    redes: dict[str, Red] = field(default_factory=dict)
    carriles: dict[str, float] = field(default_factory=dict)


def lineas(tabla: str) -> list[tuple[str, str]]:
    return HECHOS[tabla][1] if tabla in HECHOS else DIMENSIONES[tabla]


def leer_ddl() -> tuple[dict[str, list[str]], set[tuple[str, str]], set[tuple[str, str]]]:
    """Columnas de cada tabla, pares (tabla, tabla referenciada) y FK que admiten nulos."""
    columnas, referencias, opcionales = {}, set(), set()
    for tabla, cuerpo in re.findall(r'CREATE TABLE (\w+)\((.*?)\);', DDL.read_text(encoding='utf-8'), flags=re.DOTALL):
        definiciones, profundidad, actual = [], 0, ''
        for caracter in cuerpo:
            profundidad += {'(': 1, ')': -1}.get(caracter, 0)
            if caracter == ',' and profundidad == 0:
                definiciones.append(actual.strip())
                actual = ''
            else:
                actual += caracter
        definiciones.append(actual.strip())
        columnas[tabla] = [d.split()[0] for d in definiciones if not d.upper().startswith(('PRIMARY KEY', 'UNIQUE'))]
        referencias |= {(tabla, destino) for destino in re.findall(r'REFERENCES (\w+)', cuerpo)}
        opcionales |= {(tabla, d.split()[0]) for d in definiciones if 'REFERENCES' in d and 'NOT NULL' not in d}
    return columnas, referencias, opcionales


def comprobar_contra_el_ddl(relaciones: list[Relacion], columnas: dict[str, list[str]], referencias: set[tuple[str, str]]) -> None:
    dibujadas = set(HECHOS) | set(DIMENSIONES)
    if dibujadas != set(columnas) or dibujadas != {t for columna in COLUMNAS for t in columna}:
        raise ValueError(f'Tablas del DDL y del dibujo no coinciden: {sorted(dibujadas ^ set(columnas))}')
    for tabla, nombres in columnas.items():
        texto = ' '.join(contenido for _, contenido in lineas(tabla))
        faltan = [n for n in nombres if n not in LINAJE and not re.search(rf'(?<![\w]){re.escape(n)}(?![\w])', texto)]
        if faltan:
            raise ValueError(f'{tabla}: columnas del DDL que no aparecen en el dibujo: {faltan}')
    pares = {(r.muchos, r.uno) for r in relaciones}
    if pares != referencias:
        raise ValueError(f'Relaciones del dibujo y del DDL no coinciden: {sorted(pares ^ referencias)}')


def dimension_de(columna: str) -> str:
    """Dimensión a la que apunta una llave sk_*; las tres fechas de la reserva son roles de dim_fecha."""
    base = re.sub(r'_(inicio|fin|llegada)$', '', columna[3:])
    return f'dim_{base}'


def relaciones(opcionales: set[tuple[str, str]]) -> list[Relacion]:
    resultado = []
    for hecho, (_, contenido) in HECHOS.items():
        for etiqueta, columna in contenido:
            if 'FK' not in etiqueta:
                continue
            if (hecho, columna) in ENLACES_ENTRE_HECHOS:
                destino, columna_destino = ENLACES_ENTRE_HECHOS[(hecho, columna)]
            else:
                destino = dimension_de(columna)
                columna_destino = DIMENSIONES[destino][0][1]
            resultado.append(Relacion(hecho, columna, destino, columna_destino, (hecho, columna) in opcionales))
    return resultado


def filas_por_hecho() -> dict[str, int]:
    with closing(sqlite3.connect(f'file:{ORO}?mode=ro', uri=True)) as conexion:
        return {hecho: conexion.execute(f'SELECT count(*) FROM {hecho}').fetchone()[0] for hecho in HECHOS}


# ---- Medidas y posiciones de las cajas ----

@cache
def _fuente(negrita: bool):
    return ImageFont.truetype(str(FUENTE), 100, index=1 if negrita else 0) if FUENTE.exists() else None


def _ancho_de_texto(texto: str, tamano: float, *, negrita: bool = False) -> float:
    fuente = _fuente(negrita)
    if fuente is None:
        return len(texto) * tamano * ANCHO_DE_CARACTER
    return fuente.getlength(texto) / 100 * tamano


def _ancho_necesario(tabla: str) -> float:
    contenido = max(_ancho_de_texto(texto, TAMANO_COLUMNA) for _, texto in lineas(tabla)) + SANGRIA_COLUMNA
    if tabla in HECHOS:
        cabecera = max(_ancho_de_texto(tabla, 7.6, negrita=True), _ancho_de_texto(f'grano: {HECHOS[tabla][0]}', 5.2)) + 4
    else:
        cabecera = _ancho_de_texto(tabla, 7.0, negrita=True) + 4
    return max(contenido, cabecera) + 4


def _alto(tabla: str) -> float:
    cabecera = ALTO_CABECERA_HECHO if tabla in HECHOS else ALTO_CABECERA_DIMENSION
    filas_de_texto = sum(0.5 if linea == DIVISOR else 1 for linea in lineas(tabla))
    return cabecera + filas_de_texto * ALTO_DE_LINEA + 3


def filas(caja: Caja) -> list[Fila]:
    y = caja.y + (ALTO_CABECERA_HECHO if caja.tabla in HECHOS else ALTO_CABECERA_DIMENSION)
    resultado = []
    for etiqueta, contenido in lineas(caja.tabla):
        if (etiqueta, contenido) == DIVISOR:
            y += ALTO_DE_LINEA / 2
            continue
        y += ALTO_DE_LINEA
        resultado.append(Fila(etiqueta, contenido, y - 1.6))
    return resultado


def _y_de_fila(caja: Caja, contenido: str) -> float:
    return next(fila.centro for fila in filas(caja) if fila.contenido == contenido)


# ---- Canales ----

def _columna_de(tabla: str) -> int:
    return next(indice for indice, columna in enumerate(COLUMNAS) if tabla in columna)


def _redes_por_canal(lista: list[Relacion]) -> dict[int, dict[str, list[tuple[str, str, str | None]]]]:
    """Para cada canal (el canal k queda a la izquierda de la columna k), las redes que lo
    usan y sus pines abstractos: (tabla, columna, marca). Una dimensión forma una sola red
    por canal, con una barra y tantas patas de gallo como FK le llegan por ese lado."""
    canales: dict[int, dict[str, list]] = {}

    def agregar(canal: int, clave: str, *pines):
        red = canales.setdefault(canal, {}).setdefault(clave, [])
        for pin in pines:
            previo = next((i for i, otro in enumerate(red) if otro[:2] == pin[:2]), None)
            if previo is None:
                red.append(pin)
            elif pin[2] == 'cero_o_uno':
                red[previo] = pin

    for relacion in lista:
        uno, muchos = _columna_de(relacion.uno), _columna_de(relacion.muchos)
        pin_uno = (relacion.uno, relacion.columna_uno, 'cero_o_uno' if relacion.opcional else 'uno')
        pin_muchos = (relacion.muchos, relacion.columna_muchos, 'muchos')
        if uno == muchos:
            canal = uno if LADO_PROPIO[relacion.uno] == 'izquierda' else uno + 1
            agregar(canal, relacion.uno, pin_uno, pin_muchos)
        elif abs(uno - muchos) == 1:
            clave = relacion.uno if relacion.uno in DIMENSIONES else f'{relacion.muchos}>{relacion.uno}'
            agregar(max(uno, muchos), clave, pin_uno, pin_muchos)
        else:
            # Llave entre hechos separados por la columna central: sube y pasa por encima.
            clave = f'{relacion.muchos}>{relacion.uno}'
            izquierda, derecha = sorted((uno, muchos))
            extremo_izquierdo = pin_uno if uno == izquierda else pin_muchos
            extremo_derecho = pin_muchos if uno == izquierda else pin_uno
            agregar(izquierda + 1, clave, extremo_izquierdo, (TOPE, '', None))
            agregar(derecha, clave, (TOPE, '', None), extremo_derecho)
    return canales


def _ancho_de_canal(indice: int, redes: dict[str, list]) -> float:
    lados = {'izquierda' if _columna_de(tabla) == indice - 1 else 'derecha'
             for pines in redes.values() for tabla, _, _ in pines if tabla != TOPE}
    holgura = sum(ZONA_DE_MARCA if lado in lados else 2 for lado in ('izquierda', 'derecha'))
    return holgura + (len(redes) - 1) * PASO_DE_CARRIL


def _cruces(izquierda: Red, derecha: Red) -> float:
    """Cruces si la red `izquierda` ocupa un carril a la izquierda de `derecha`. Un pin a la
    misma altura que el extremo de la otra red se superpondría con ella: cuenta como cinco."""
    def contar(pines, extremos):
        bajo, alto = extremos
        return sum(5 if pin.y in (bajo, alto) else 1 for pin in pines if bajo <= pin.y <= alto)
    return (contar([p for p in izquierda.pines if p.lado == 'derecha'], derecha.extremos)
            + contar([p for p in derecha.pines if p.lado == 'izquierda'], izquierda.extremos))


def _asignar_carriles(canal: Canal) -> None:
    claves = list(canal.redes)
    con_pines_a_la_izquierda = any(p.lado == 'izquierda' for red in canal.redes.values() for p in red.pines)
    con_pines_a_la_derecha = any(p.lado == 'derecha' for red in canal.redes.values() for p in red.pines)
    inicio = canal.x0 + (ZONA_DE_MARCA if con_pines_a_la_izquierda else 2)
    fin = canal.x1 - (ZONA_DE_MARCA if con_pines_a_la_derecha else 2)
    posiciones = [(inicio + fin) / 2] if len(claves) == 1 else [inicio + i * (fin - inicio) / (len(claves) - 1) for i in range(len(claves))]
    costo = {(a, b): _cruces(canal.redes[a], canal.redes[b]) for a in claves for b in claves if a != b}

    def largo(orden):
        return sum(abs(x - (canal.x0 if pin.lado == 'izquierda' else canal.x1))
                   for x, clave in zip(posiciones, orden, strict=True) for pin in canal.redes[clave].pines)

    def puntaje(orden):
        cruces = sum(costo[orden[i], orden[j]] for i in range(len(orden)) for j in range(i + 1, len(orden)))
        return cruces, largo(orden)

    mejor = min(itertools.permutations(claves), key=puntaje)
    canal.carriles = dict(zip(mejor, posiciones, strict=True))


# ---- Disposición ----

def disponer(lista: list[Relacion]) -> tuple[dict[str, Caja], list[Canal]]:
    abstractas = _redes_por_canal(lista)
    anchos_de_columna = [max(_ancho_necesario(t) for t in columna) for columna in COLUMNAS]

    canales, cajas, x = [], {}, 0.0
    for indice in range(len(COLUMNAS) + 1):
        ancho = _ancho_de_canal(indice, abstractas[indice]) if indice in abstractas else 2
        canales.append(Canal(x, x + ancho))
        x += ancho
        if indice < len(COLUMNAS):
            separacion = SEPARACION_CENTRAL if indice == 1 else SEPARACION_LATERAL
            y = MARGEN_SUPERIOR
            for tabla in COLUMNAS[indice]:
                cajas[tabla] = Caja(tabla, x, y, anchos_de_columna[indice], _alto(tabla))
                y += _alto(tabla) + separacion
            x += anchos_de_columna[indice]

    for indice, redes in abstractas.items():
        canal = canales[indice]
        for clave, pines in redes.items():
            red = canal.redes.setdefault(clave, Red(punteada=clave not in DIMENSIONES))
            for tabla, columna, marca in pines:
                if tabla == TOPE:
                    lado = 'derecha' if any(t != TOPE and _columna_de(t) == indice - 1 for t, _, _ in pines) else 'izquierda'
                    red.pines.append(Pin(lado, MARGEN_SUPERIOR / 2, None))
                    continue
                lado = 'izquierda' if _columna_de(tabla) == indice - 1 else 'derecha'
                red.pines.append(Pin(lado, _y_de_fila(cajas[tabla], columna), marca))
        _asignar_carriles(canal)
    return cajas, canales


# ---- Dibujo ----

def _texto(x, y, contenido, tamano, *, peso='normal', color=TINTA, ancla='start', familia=None) -> str:
    estilo = f' font-family="{familia}"' if familia else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{tamano}" font-weight="{peso}" fill="{color}" '
            f'text-anchor="{ancla}"{estilo}>{escape(contenido)}</text>')


def _caja(caja: Caja) -> list[str]:
    es_hecho = caja.tabla in HECHOS
    partes = [f'<rect x="{caja.x:.1f}" y="{caja.y:.1f}" width="{caja.ancho:.1f}" height="{caja.alto:.1f}" '
              f'fill="#fff" stroke="{TINTA if es_hecho else "#9f9f9f"}" stroke-width="{0.7 if es_hecho else 0.5}" />']
    if es_hecho:
        partes += [f'<rect x="{caja.x:.1f}" y="{caja.y:.1f}" width="{caja.ancho:.1f}" height="{ALTO_CABECERA_HECHO}" fill="{TINTA}" />',
                   _texto(caja.x + 4, caja.y + 7.4, caja.tabla, 7.6, peso='bold', color='#fff'),
                   _texto(caja.x + 4, caja.y + 13.4, f'grano: {HECHOS[caja.tabla][0]}', 5.2, color='#e0e0e0')]
    else:
        partes += [f'<rect x="{caja.x:.1f}" y="{caja.y:.1f}" width="{caja.ancho:.1f}" height="{ALTO_CABECERA_DIMENSION}" fill="#ececec" />',
                   _texto(caja.x + 4, caja.y + 7.6, caja.tabla, 7.0, peso='bold')]
    y = caja.y + (ALTO_CABECERA_HECHO if es_hecho else ALTO_CABECERA_DIMENSION)
    for etiqueta, contenido in lineas(caja.tabla):
        if (etiqueta, contenido) == DIVISOR:
            partes.append(f'<path d="M{caja.x + 3:.1f} {y + 1.8:.1f} H{caja.derecha - 3:.1f}" stroke="#c8c8c8" '
                          'stroke-width="0.4" stroke-dasharray="1.4 1" />')
            y += ALTO_DE_LINEA / 2
            continue
        y += ALTO_DE_LINEA
        if etiqueta == '§':
            partes.append(_texto(caja.x + 3.5, y - 1.6, contenido.upper(), 4.4, peso='bold', color=GRIS))
            continue
        partes.append(_texto(caja.x + 3.5, y - 1.6, etiqueta, 4.4, peso='bold', color=GRIS))
        partes.append(_texto(caja.x + SANGRIA_COLUMNA, y - 1.6, contenido, TAMANO_COLUMNA, color=GRIS if etiqueta == '+' else TINTA))
    return partes


def _estilo(punteada: bool) -> str:
    return f'stroke="{LINEA_RELACION}" stroke-width="0.55" fill="none"' + (' stroke-dasharray="1.8 1.2"' if punteada else '')


def _marca(x_borde: float, y: float, marca: str | None, hacia_adentro: int) -> str:
    """Barra (uno) o pata de gallo (muchos) junto al borde de la caja; `hacia_adentro` es
    +1 si el canal queda a la derecha del borde y -1 si queda a la izquierda."""
    if marca in ('uno', 'cero_o_uno'):
        x = x_borde + hacia_adentro * 2.5
        barra = f'<path d="M{x:.1f} {y - 2.4:.1f} V{y + 2.4:.1f}" stroke="{LINEA_RELACION}" stroke-width="0.8" />'
        if marca == 'uno':
            return barra
        centro = x_borde + hacia_adentro * 4.9
        return barra + f'<circle cx="{centro:.1f}" cy="{y:.1f}" r="1.05" fill="#fff" stroke="{LINEA_RELACION}" stroke-width="0.55" />'
    if marca == 'muchos':
        vertice = x_borde + hacia_adentro * 4.2
        return (f'<path d="M{vertice:.1f} {y:.1f} L{x_borde:.1f} {y - 2.3:.1f} M{vertice:.1f} {y:.1f} L{x_borde:.1f} {y + 2.3:.1f}" '
                f'stroke="{LINEA_RELACION}" stroke-width="0.6" fill="none" />')
    return ''


def _canal(canal: Canal) -> list[str]:
    partes = []
    for clave, red in canal.redes.items():
        x = canal.carriles[clave]
        bajo, alto = red.extremos
        estilo = _estilo(red.punteada)
        if alto > bajo:
            partes.append(f'<path d="M{x:.1f} {bajo:.1f} V{alto:.1f}" {estilo} />')
        for pin in red.pines:
            x_borde, hacia_adentro = (canal.x0, 1) if pin.lado == 'izquierda' else (canal.x1, -1)
            partes.append(f'<path d="M{x_borde:.1f} {pin.y:.1f} H{x:.1f}" {estilo} />')
            partes.append(_marca(x_borde, pin.y, pin.marca, hacia_adentro))
            tramos = sum(1 for otro in red.pines if otro.y == pin.y) + (pin.y > bajo) + (pin.y < alto)
            if tramos >= 3:
                partes.append(f'<circle cx="{x:.1f}" cy="{pin.y:.1f}" r="0.95" fill="{LINEA_RELACION}" />')
    return partes


def _tramos_por_encima(canales: list[Canal]) -> list[str]:
    """Une, sobre la columna central, las dos mitades de cada llave que pasa por arriba."""
    partes = []
    for izquierdo, derecho in itertools.pairwise(canales):
        for clave, red in izquierdo.redes.items():
            if clave in derecho.redes and any(p.marca is None for p in red.pines):
                partes.append(f'<path d="M{izquierdo.x1:.1f} {MARGEN_SUPERIOR / 2:.1f} H{derecho.x0:.1f}" {_estilo(red.punteada)} />')
    return partes


def _leyenda(x: float, y: float, filas_de_hechos: dict[str, int]) -> list[str]:
    paso = 8.5
    partes = [
        f'<rect x="{x:.1f}" y="{y - 4.5:.1f}" width="9" height="5" fill="{TINTA}" />',
        _texto(x + 12, y, 'tabla de hechos', TAMANO_COLUMNA),
        f'<rect x="{x + 62:.1f}" y="{y - 4.5:.1f}" width="9" height="5" fill="#ececec" stroke="#9f9f9f" stroke-width="0.5" />',
        _texto(x + 74, y, 'dimensión', TAMANO_COLUMNA),
    ]
    muestras = [('uno', False, 'una fila de la dimensión, muchas del hecho'),
                ('cero_o_uno', False, 'cero o una: la FK admite nulos'),
                ('uno', True, 'llave entre dos hechos')]
    for indice, (marca, punteada, texto) in enumerate(muestras, start=1):
        base = y + paso * indice - 2
        partes += [f'<path d="M{x:.1f} {base:.1f} H{x + 22:.1f}" {_estilo(punteada)} />',
                   _marca(x, base, marca, 1), _marca(x + 22, base, 'muchos', -1),
                   _texto(x + 26, base + 2, texto, TAMANO_COLUMNA)]
    partes.append(_texto(x, y + paso * 4, 'PK llave primaria · FK llave foránea · › jerarquía', TAMANO_COLUMNA, color=GRIS))

    y_filas = y + paso * 5.6
    partes.append(_texto(x, y_filas, 'Filas en la capa oro', TAMANO_COLUMNA, peso='bold'))
    for indice, (hecho, cantidad) in enumerate(filas_de_hechos.items(), start=1):
        base = y_filas + ALTO_DE_LINEA * indice
        partes += [_texto(x, base, hecho, TAMANO_COLUMNA),
                   _texto(x + 82, base, f'{cantidad:,}'.replace(',', '.'), TAMANO_COLUMNA, ancla='end')]
    return partes


def dibujar() -> str:
    columnas, referencias, opcionales = leer_ddl()
    lista = relaciones(opcionales)
    comprobar_contra_el_ddl(lista, columnas, referencias)
    cajas, canales = disponer(lista)
    ancho_total = canales[-1].x1
    alto_total = max(caja.abajo for caja in cajas.values())
    columna_encuesta = [cajas[t] for t in COLUMNAS[2] + COLUMNAS[3]]
    y_leyenda = max(caja.abajo for caja in columna_encuesta) + 16

    cuerpo = [parte for canal in canales for parte in _canal(canal)]
    cuerpo += _tramos_por_encima(canales)
    cuerpo += [parte for caja in cajas.values() for parte in _caja(caja)]
    cuerpo += _leyenda(min(caja.x for caja in columna_encuesta), y_leyenda, filas_por_hecho())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 {ancho_total + 2:.1f} {alto_total + 2:.1f}" '
            'font-family="Helvetica Neue, Helvetica, Arial, sans-serif">' + ''.join(cuerpo) + '</svg>')


def main() -> None:
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(dibujar(), encoding='utf-8')
    print(f'{DESTINO.relative_to(RAIZ)}: 14 tablas y sus relaciones comprobadas contra {DDL.relative_to(RAIZ)}')


if __name__ == '__main__':
    main()
