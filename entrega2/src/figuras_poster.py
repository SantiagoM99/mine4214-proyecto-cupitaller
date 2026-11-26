"""Gráficas y recortes de documentos para el póster de 70 × 100 cm.

    python3 src/figuras_poster.py

Cada gráfica se dibuja al tamaño al que se imprime, así que los tamaños de letra de
este archivo son los del papel. El color no distingue series: la que importa va en
tinta, las demás en gris, y el amarillo marca la zona que hay que mirar. Verde y
rojo quedan reservados para acierto y fallo.
"""

import sqlite3

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
from PIL import Image, ImageChops

from config import BODEGA, DIR_PAGINAS, PREGUNTAS, RAIZ
from evaluar import ARCHIVO_RESUMEN, ARCHIVO_VEREDICTOS, leer_json
from figuras import DIR_FIGURAS, numero, periodo_legible
from temas_por_nivel import por_nivel

DIR_POSTER = RAIZ / 'docs' / 'poster'
DIR_GRAFICAS = DIR_POSTER / 'figuras'
DIR_IMAGENES = DIR_POSTER / 'img'

MM = 1 / 25.4
ANCHO_MM = 206  # ancho útil de una columna del póster

TINTA = '#1c1c1c'
GRIS = '#a6a6a6'
GRIS_CLARO = '#e2e2e2'
AMARILLO = '#ffd200'
ROJO = '#d23b3b'

FILAS_DE_ACIERTOS = (('directo', 'Prompting directo'), ('rag_visual', 'RAG visual'), ('rag_texto', 'RAG de texto'))
CATEGORIAS = {
    'programa': 'Programa\ndel curso',
    'diapositiva_texto': 'Diapositiva:\ntexto',
    'diapositiva_imagen': 'Diapositiva:\nimagen',
    'alcance_por_nivel': 'Alcance\npor nivel',
    'no_respondible': 'Sin\nrespuesta',
}
CATEGORIA_RESALTADA = 'diapositiva_imagen'
SEMESTRES_DE_DEMANDA = ('202410', '202420', '202510')
PRIMER_SEMESTRE_SIN_GRUPALES = '202210'
ANCHO_DEL_FUNDIDO_PX = 120
# De 202210 a 202410 la categoría de los horarios cubre 45 % o menos de las atenciones (Entrega 1).
COBERTURA_COMPARABLE_PCT = 75

plt.rcParams.update({
    'font.family': ['Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans'],
    'font.size': 16, 'text.color': TINTA,
    'axes.edgecolor': '#9a9a9a', 'axes.labelcolor': TINTA, 'axes.labelsize': 16, 'axes.linewidth': 1.0,
    'axes.spines.top': False, 'axes.spines.right': False,
    'xtick.color': TINTA, 'ytick.color': TINTA, 'xtick.labelsize': 15.5, 'ytick.labelsize': 15.5,
    'xtick.major.size': 0, 'ytick.major.size': 0,
    'grid.color': GRIS_CLARO, 'grid.linewidth': 1.0, 'legend.fontsize': 16,
    'svg.fonttype': 'none',
})


def lienzo(alto_mm: float, *args, **kwargs):
    """`plt.subplots` con el ancho de una columna del póster y el alto dado, en milímetros."""
    return plt.subplots(*args, figsize=(ANCHO_MM * MM, alto_mm * MM), **kwargs)


def guardar(figura: plt.Figure, nombre: str) -> None:
    DIR_GRAFICAS.mkdir(parents=True, exist_ok=True)
    figura.savefig(DIR_GRAFICAS / f'{nombre}.svg', bbox_inches='tight', pad_inches=0.02, transparent=True)
    plt.close(figura)


def grafica_grupales() -> None:
    """Reservas de tutoría grupal por semestre: la evidencia de que el programa de 2020-20 quedó desactualizado."""
    semestres = [f'{anio}{sufijo}' for anio in range(2017, 2027) for sufijo in ('10', '20')][:-1]
    with sqlite3.connect(BODEGA) as bodega:
        reservas = dict(bodega.execute(
            "SELECT periodo, sum(reservas) FROM agg_tipos_de_horario WHERE tipo_horario LIKE '%Grupal%' GROUP BY periodo"
        ).fetchall())
    figura, ejes = lienzo(56)
    ejes.bar(range(len(semestres)), [reservas.get(semestre, 0) for semestre in semestres], 0.74, color=TINTA)
    desde = semestres.index(PRIMER_SEMESTRE_SIN_GRUPALES)
    ejes.axvspan(desde - 0.5, len(semestres) - 0.5, color=AMARILLO, alpha=0.75, linewidth=0)
    ejes.text((desde + len(semestres) - 1) / 2, 105, f'ninguna desde\n{periodo_legible(PRIMER_SEMESTRE_SIN_GRUPALES)}',
              ha='center', va='center', fontsize=19, fontweight='bold', linespacing=1.15)
    ejes.set_xticks([indice + 0.5 for indice in range(0, len(semestres) - 1, 2)], [semestre[:4] for semestre in semestres[::2]][:-1])
    ejes.set_xlim(-0.7, len(semestres) - 0.5)
    ejes.set_yticks([0, 100, 200])
    ejes.yaxis.grid(True)
    ejes.set_axisbelow(True)
    ejes.spines['left'].set_visible(False)
    guardar(figura, 'grupales_por_semestre')


def grafica_aciertos_por_pregunta() -> None:
    """Un cuadro por pregunta y sistema, agrupados por tipo de pregunta."""
    preguntas = leer_json(PREGUNTAS, [])
    veredictos = leer_json(ARCHIVO_VEREDICTOS, {})
    resumen = leer_json(ARCHIVO_RESUMEN, {})
    relleno = {'correcta': (TINTA, TINTA), 'parcial': (GRIS, GRIS), 'incorrecta': ('white', ROJO)}
    lado, separacion_de_grupos, alto_de_fila, alto_de_rotulo = 0.84, 1.1, 2.45, 1.08

    # Posición horizontal de cada pregunta: las de un mismo tipo van juntas.
    columna_de = {}
    x = 0.0
    figura, ejes = lienzo(66)
    for categoria, etiqueta in CATEGORIAS.items():
        del_grupo = [pregunta for pregunta in preguntas if pregunta['categoria'] == categoria]
        if categoria == CATEGORIA_RESALTADA:
            for fila in range(len(FILAS_DE_ACIERTOS)):
                ejes.add_patch(Rectangle((x - 0.24, fila * alto_de_fila + alto_de_rotulo - 0.22), len(del_grupo) + 0.32, lado + 0.44,
                                         facecolor=AMARILLO, alpha=0.8, linewidth=0, zorder=0))
        ejes.text(x + len(del_grupo) / 2 - 0.08, -0.6, etiqueta, ha='center', va='bottom', fontsize=14, linespacing=1.05)
        for posicion, pregunta in enumerate(del_grupo):
            columna_de[pregunta['id']] = x + posicion
        x += len(del_grupo) + separacion_de_grupos

    for fila, (sistema, nombre) in enumerate(FILAS_DE_ACIERTOS):
        arriba = fila * alto_de_fila
        correctas = round(resumen[sistema]['correctas_pct'] * resumen[sistema]['preguntas'] / 100)
        rotulo = ejes.text(0, arriba + 0.36, nombre, ha='left', va='center', fontsize=16, fontweight='bold')
        ejes.annotate(f"{correctas} de {resumen[sistema]['preguntas']} correctas", xy=(1, 0.5), xycoords=rotulo,
                      xytext=(9, 0), textcoords='offset points', ha='left', va='center', fontsize=16)
        for pregunta in preguntas:
            cara, borde = relleno[veredictos[f"{pregunta['id']}|{sistema}"]['veredicto']]
            ejes.add_patch(Rectangle((columna_de[pregunta['id']], arriba + alto_de_rotulo), lado, lado,
                                     facecolor=cara, edgecolor=borde, linewidth=1.8))
    ejes.set_xlim(-0.4, x - separacion_de_grupos + 0.3)
    ejes.set_ylim(alto_de_fila * len(FILAS_DE_ACIERTOS) + 0.1, -2.9)
    ejes.set_aspect('equal')
    ejes.axis('off')
    ejes.legend(
        handles=[Patch(facecolor=TINTA, label='correcta'), Patch(facecolor=GRIS, label='parcial'),
                 Patch(facecolor='white', edgecolor=ROJO, linewidth=1.8, label='incorrecta')],
        frameon=False, ncols=3, loc='upper center', bbox_to_anchor=(0.5, 0.03), handlelength=0.9, handleheight=0.9, columnspacing=1.6,
    )
    guardar(figura, 'aciertos_por_pregunta')


def grafica_costo() -> None:
    resumen = leer_json(ARCHIVO_RESUMEN, {})
    barras = [
        ('Directo sin caché', 1000 * resumen['directo']['costo_usd_por_consulta_sin_cache'], TINTA),
        ('Directo con caché', 1000 * resumen['directo']['costo_usd_por_consulta'], TINTA),
        ('RAG visual', 1000 * resumen['rag_visual']['costo_usd_por_consulta'], TINTA),
    ]
    figura, ejes = lienzo(35)
    ejes.barh(range(len(barras)), [valor for _, valor, _ in barras], 0.6, color=[color for _, _, color in barras])
    for posicion, (_, valor, _) in enumerate(barras):
        ejes.text(valor + 0.18, posicion, f'US$ {numero(valor, 2)}', va='center', fontsize=17.5, fontweight='bold')
    ejes.set_yticks(range(len(barras)), [nombre for nombre, _, _ in barras], fontsize=17)
    ejes.invert_yaxis()
    ejes.set_xlim(0, 13.8)
    ejes.set_xticks([])
    ejes.spines['bottom'].set_visible(False)
    guardar(figura, 'costo_por_mil_consultas')


def grafica_analisis_entrega1() -> None:
    """Los dos análisis de la Entrega 1 por modalidad: inasistencia y calificaciones bajas."""
    with sqlite3.connect(BODEGA) as bodega:
        inasistencia = dict(bodega.execute(
            """SELECT tipo_tutoria, 100.0 * sum(estado = 'No asistió') / sum(estado IN ('Atendida', 'No asistió'))
               FROM v_reservas GROUP BY 1"""
        ).fetchall())
        bajas = dict(bodega.execute(
            """SELECT tipo_tutoria, 100.0 * sum(calificacion_tutor <= 3) / count(calificacion_tutor)
               FROM v_encuestas WHERE etapa = 'posterior' GROUP BY 1"""
        ).fetchall())
    modalidades = ['Normal', 'Express', 'Normal pico']
    paneles = (('Inasistencia', inasistencia, 'Express'), ('Calificaciones de 1 a 3', bajas, 'Normal pico'))
    figura, ejes = lienzo(58, 1, 2, gridspec_kw={'wspace': 0.12}, sharey=True)
    for panel, (titulo, valores, resaltada) in zip(ejes, paneles, strict=True):
        datos = [valores[modalidad] for modalidad in modalidades]
        panel.barh(range(len(modalidades)), datos, 0.64,
                   color=[TINTA if modalidad == resaltada else GRIS for modalidad in modalidades])
        for posicion, (modalidad, valor) in enumerate(zip(modalidades, datos, strict=True)):
            panel.text(valor + 0.4, posicion, f'{numero(valor, 1)} %', va='center',
                       fontsize=16.5, fontweight='bold' if modalidad == resaltada else 'normal')
        panel.set_title(titulo, loc='left', fontsize=16.5, fontweight='bold', pad=8)
        panel.set_xlim(0, 20)
        panel.set_xticks([])
        panel.spines['bottom'].set_visible(False)
    ejes[0].set_yticks(range(len(modalidades)), modalidades, fontsize=16)
    ejes[0].invert_yaxis()
    ejes[1].spines['left'].set_visible(False)
    guardar(figura, 'analisis_entrega1')


def _en_renglones(nombres: list[str], ancho: int) -> str:
    """Une los nombres con «·» y parte el texto entre nombres, nunca dentro de uno."""
    renglones: list[str] = []
    for nombre in nombres:
        if renglones and len(renglones[-1]) + 3 + len(nombre) <= ancho:
            renglones[-1] += f' · {nombre}'
        else:
            renglones.append(nombre)
    return '\n'.join(renglones)


def grafica_temas_por_nivel() -> None:
    """Clases de 2026-20 de cada nivel con y sin versión en el material de 2020-21, y cuáles no la tienen."""
    niveles = por_nivel()
    figura, ejes = lienzo(58)
    for fila, nivel in enumerate(niveles):
        con, sin = len(nivel.con_version), len(nivel.sin_version)
        ejes.barh(fila, con, 0.62, color=GRIS)
        ejes.barh(fila, sin, 0.62, left=con, color=TINTA)
        ejes.text(con / 2, fila, str(con), ha='center', va='center', fontsize=15)
        ejes.text(con + sin / 2, fila, str(sin), ha='center', va='center', fontsize=15, color='white', fontweight='bold')
        ejes.text(con + sin + 0.4, fila, _en_renglones(nivel.sin_version, 47), va='center',
                  fontsize=13, linespacing=1.2)
    ejes.set_yticks(range(len(niveles)), [f'Nivel {nivel.nivel}' for nivel in niveles], fontsize=15.5)
    ejes.invert_yaxis()
    ejes.set_xlim(0, 24)
    ejes.set_xticks([])
    ejes.spines['bottom'].set_visible(False)
    ejes.legend(handles=[Patch(color=GRIS, label='con versión en 2020-21'), Patch(color=TINTA, label='sin versión en el material de 2020-21')],
                loc='lower left', bbox_to_anchor=(-0.02, 1.0), ncol=2, frameon=False, fontsize=13.5,
                handlelength=1.0, handletextpad=0.4, columnspacing=1.2)
    # El informe usa la misma gráfica, en PDF.
    figura.savefig(DIR_FIGURAS / 'temas_por_nivel.pdf', bbox_inches='tight')
    guardar(figura, 'temas_por_nivel')


def _tramos_consecutivos(indices: list[int]) -> list[list[int]]:
    """[3, 4, 5, 9] -> [[3, 4, 5], [9]]."""
    tramos: list[list[int]] = []
    for indice in indices:
        if tramos and indice == tramos[-1][-1] + 1:
            tramos[-1].append(indice)
        else:
            tramos.append([indice])
    return tramos


def grafica_ocupacion_por_semestre() -> None:
    """Ocupación de la oferta por semestre, solo donde la categoría cubre la mayoría de las atenciones."""
    with sqlite3.connect(BODEGA) as bodega:
        ocupacion = dict(bodega.execute(
            f"""SELECT periodo, ocupacion_pct FROM agg_oferta_periodo
                WHERE ocupacion_pct IS NOT NULL AND atenciones_cubiertas_pct >= {COBERTURA_COMPARABLE_PCT}
                ORDER BY periodo"""
        ).fetchall())
    # Eje de tiempo continuo: un semestre sin datos comparables deja su hueco en vez de juntar las barras vecinas.
    semestres = [f'{anio}{sufijo}' for anio in range(2010, 2040) for sufijo in ('10', '20')]
    semestres = semestres[semestres.index(min(ocupacion)):semestres.index(max(ocupacion)) + 1]
    posicion = {semestre: indice for indice, semestre in enumerate(semestres)}
    recientes = sorted(ocupacion)[-2:]

    figura, ejes = lienzo(55)
    ejes.bar([posicion[s] for s in ocupacion], list(ocupacion.values()), 0.72,
             color=[TINTA if s in recientes else GRIS for s in ocupacion])
    for huecos in _tramos_consecutivos([posicion[s] for s in semestres if s not in ocupacion]):
        ejes.axvspan(huecos[0] - 0.5, huecos[-1] + 0.5, color='#efefef', linewidth=0)
        ejes.text((huecos[0] + huecos[-1]) / 2, 50, 'sin datos\ncomparables', ha='center', va='center',
                  fontsize=12, color='#7a7a7a', linespacing=1.2)

    centro = sum(posicion[s] for s in recientes) / 2
    # La etiqueta va sobre las barras vecinas, más altas, para no tocarlas.
    vecinas = [valor for s, valor in ocupacion.items() if abs(posicion[s] - centro) <= 2]
    ejes.text(centro, max(vecinas) + 4, f'{numero(min(ocupacion[s] for s in recientes))} a {numero(max(ocupacion[s] for s in recientes))} %',
              ha='center', va='bottom', fontsize=16, fontweight='bold')

    anios = sorted({s[:4] for s in semestres})
    ejes.set_xticks([sum(posicion[s] for s in semestres if s[:4] == anio) / sum(1 for s in semestres if s[:4] == anio) for anio in anios],
                    anios, fontsize=13)
    ejes.tick_params(axis='x', length=0)
    ejes.set_xlim(-0.6, len(semestres) - 0.4)
    ejes.set_ylim(0, 100)
    ejes.set_yticks([50, 100], ['50 %', '100 %'])
    ejes.yaxis.grid(True)
    ejes.set_axisbelow(True)
    ejes.spines['left'].set_visible(False)
    guardar(figura, 'ocupacion_por_semestre')


def _pagina(clave: str, numero_de_pagina: int) -> Image.Image:
    return Image.open(DIR_PAGINAS / clave / f'p{numero_de_pagina:03d}.png').convert('RGB')


def recortes() -> None:
    """Imágenes de los documentos reales que muestra el póster."""
    DIR_IMAGENES.mkdir(parents=True, exist_ok=True)
    _pagina('2026-20_n3_08_patrones-de-recorrido', 5).save(DIR_IMAGENES / 'diapositiva_n3_08_p5.png')

    # Párrafo de la página 5 del programa de 2020-20 que enumera los tipos de tutoría.
    # Las cajas están en píxeles de la página renderizada a 1.237 × 1.600.
    programa = _pagina('2020-20_programa', 5)
    frase = (108, 684, 742, 718)
    resaltada = ImageChops.multiply(programa.crop(frase), Image.new('RGB', (frase[2] - frase[0], frase[3] - frase[1]), (255, 216, 0)))
    programa.paste(resaltada, frase)
    recorte = programa.crop((100, 670, 830, 766))
    # El párrafo sigue a la derecha del recorte; el fundido a blanco muestra que el corte es deliberado.
    fundido = Image.linear_gradient('L').rotate(90).resize((ANCHO_DEL_FUNDIDO_PX, recorte.height))
    recorte.paste(Image.new('RGB', fundido.size, 'white'), (recorte.width - ANCHO_DEL_FUNDIDO_PX, 0), fundido)
    recorte.save(DIR_IMAGENES / 'programa_2020_tipos_de_tutoria.png')

    for clave, nombre in (('2020-20_programa', 'programa_2020_p5.png'), ('2026-20_programa', 'programa_2026_p5.png')):
        miniatura = _pagina(clave, 5)
        miniatura.thumbnail((520, 700))
        miniatura.save(DIR_IMAGENES / nombre)


def main() -> None:
    for grafica in (grafica_grupales, grafica_aciertos_por_pregunta, grafica_costo,
                    grafica_analisis_entrega1,
                    grafica_ocupacion_por_semestre, grafica_temas_por_nivel):
        grafica()
        print(f'  {grafica.__name__}')
    recortes()
    print('  recortes')


if __name__ == '__main__':
    main()
