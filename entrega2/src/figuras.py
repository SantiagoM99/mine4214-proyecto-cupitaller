"""Gráficas del informe, a partir de los resultados guardados.

    python3 src/figuras.py

Escribe cada figura como PDF en docs/figuras/. Las del póster tienen otro tamaño y
otra paleta y están en src/figuras_poster.py.
"""

import sqlite3

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import psycopg
from matplotlib.patches import Rectangle

from config import BODEGA, DATABASE_URL, RAIZ
from evaluar import ARCHIVO_RESUMEN, SISTEMAS, leer_json
from poc_entropia import ARCHIVO as ARCHIVO_ENTROPIA
from poc_entropia import CONFIGURACIONES, PREGUNTAS_DE_VIGENCIA

DIR_FIGURAS = RAIZ / 'docs' / 'figuras'

TINTA = '#191919'
TINTA_SECUNDARIA = '#666666'
REJILLA = '#e7e7e7'
EJE = '#c2c2c2'

# Un color por sistema, fijo en todas las figuras.
COLOR = {'directo': '#257de0', 'rag_texto': '#f47230', 'rag_visual': '#00b894'}
NOMBRE = {'directo': 'Prompting directo', 'rag_texto': 'RAG de texto', 'rag_visual': 'RAG visual'}

CATEGORIAS = {
    'programa': 'Programa\ndel curso',
    'diapositiva_texto': 'Diapositiva\n(texto)',
    'diapositiva_imagen': 'Diapositiva\n(imagen)',
    'alcance_por_nivel': 'Alcance\npor nivel',
    'no_respondible': 'Sin\nrespuesta',
}

CONFIGURACION = {
    'rag_ingenuo_texto': 'RAG ingenuo\n(solo texto)',
    'rag_ingenuo_visual': 'RAG ingenuo\n(visual)',
    'rag_con_etiquetas': 'RAG con\netiqueta de semestre',
    'rag_filtro_vigente': 'RAG con\nfiltro de vigencia',
    'directo_dos_programas': 'Directo con\nlos dos programas',
}
PREGUNTA_DE_VIGENCIA = {
    'vig-01': 'Tipos de tutoría en CupiTaller',
    'vig-02': 'Peso del Nivel 2',
    'vig-03': 'Peso del Nivel 4',
    'vig-04': '¿El proyecto tiene nota?',
    'vig-05': 'Cláusula de arrepentimiento',
    'vig-06': 'Plataforma del curso',
}
# clase: (fondo, texto de la celda). El texto lleva la respuesta; el color solo la refuerza.
CLASE = {
    'vigente': ('#d9f2dd', '✓ vigente'),
    'ambas_distinguiendo': ('#d9f2dd', '✓ distingue\nlas versiones'),
    'desactualizada': ('#f8d7d7', '✗ desactualizada'),
    'ambas_sin_distinguir': ('#fde9c4', '! mezcla\nversiones'),
    'abstencion': ('#efefef', '– se abstiene'),
}

SEMESTRES_DE_DEMANDA = ('202410', '202420', '202510', '202610')

plt.rcParams.update({
    'font.family': ['Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans'],
    'font.size': 9, 'text.color': TINTA,
    'axes.edgecolor': EJE, 'axes.labelcolor': TINTA_SECUNDARIA, 'axes.titlesize': 10,
    'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
    'axes.spines.top': False, 'axes.spines.right': False,
    'xtick.color': TINTA_SECUNDARIA, 'ytick.color': TINTA_SECUNDARIA,
    'xtick.major.size': 0, 'ytick.major.size': 0,
    'axes.grid': False, 'grid.color': REJILLA, 'grid.linewidth': 0.6,
    'svg.fonttype': 'none', 'pdf.fonttype': 42,
})


def lienzo(ancho: float, alto: float, *args, **kwargs):
    """`plt.subplots` con el tamaño de la figura en pulgadas."""
    return plt.subplots(*args, figsize=(ancho, alto), **kwargs)


def guardar(figura: plt.Figure, nombre: str) -> None:
    DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    figura.savefig(DIR_FIGURAS / f'{nombre}.pdf', bbox_inches='tight')
    plt.close(figura)


def numero(valor: float, decimales: int = 0) -> str:
    """Número con separadores en español: punto para miles y coma decimal."""
    return f'{valor:,.{decimales}f}'.replace(',', ' ').replace('.', ',').replace(' ', '.')


def periodo_legible(periodo: str) -> str:
    return f'{periodo[:4]}-{periodo[4:]}'


def figura_exactitud() -> None:
    resumen = leer_json(ARCHIVO_RESUMEN, {})
    figura, ejes = lienzo(7.2, 3.1)
    ancho = 0.26
    for desplazamiento, sistema in enumerate(SISTEMAS):
        for posicion, categoria in enumerate(CATEGORIAS):
            grupo = resumen[sistema]['por_categoria'][categoria]
            x = posicion + (desplazamiento - 1) * ancho
            ejes.bar(x, grupo['correctas'], ancho - 0.03, color=COLOR[sistema],
                     label=NOMBRE[sistema] if posicion == 0 else None)
            ejes.text(x, grupo['correctas'] + 0.12, f"{grupo['correctas']}/{grupo['preguntas']}",
                      ha='center', va='bottom', fontsize=7.5)
    ejes.set_xticks(range(len(CATEGORIAS)), CATEGORIAS.values())
    ejes.set_ylabel('Respuestas correctas')
    ejes.set_ylim(0, 8.4)
    ejes.yaxis.grid(True)
    ejes.set_axisbelow(True)
    ejes.spines['left'].set_visible(False)
    ejes.legend(frameon=False, ncols=3, loc='lower left', bbox_to_anchor=(-0.02, 1.0), columnspacing=1.2, handlelength=1.2)
    guardar(figura, 'exactitud_por_categoria')


def _barras_horizontales(ejes, etiquetas: list[str], valores: list[float], colores: list[str], decimales: int) -> None:
    posiciones = range(len(valores))
    ejes.barh(posiciones, valores, 0.62, color=colores)
    for posicion, valor in zip(posiciones, valores, strict=True):
        ejes.text(valor + max(valores) * 0.02, posicion, numero(valor, decimales), va='center', fontsize=8.5)
    ejes.set_yticks(posiciones, etiquetas)
    ejes.invert_yaxis()
    ejes.set_xlim(0, max(valores) * 1.32)
    ejes.set_xticks([])
    ejes.spines['bottom'].set_visible(False)
    ejes.tick_params(axis='y', colors=TINTA)


def figura_costo_y_latencia() -> None:
    resumen = leer_json(ARCHIVO_RESUMEN, {})
    figura, (tokens, costo, latencia) = lienzo(9.6, 2.1, 1, 3, gridspec_kw={'wspace': 1.25})
    nombres = [NOMBRE[sistema] for sistema in SISTEMAS]
    colores = [COLOR[sistema] for sistema in SISTEMAS]
    tokens.set_title('Tokens de entrada\npor consulta')
    _barras_horizontales(tokens, nombres, [resumen[s]['tokens_entrada_promedio'] for s in SISTEMAS], colores, 0)
    costo.set_title('Costo por 1.000 consultas\n(USD)')
    _barras_horizontales(
        costo,
        ['Directo, sin caché', 'Directo, caché caliente', NOMBRE['rag_texto'], NOMBRE['rag_visual']],
        [1000 * resumen['directo']['costo_usd_por_consulta_sin_cache'], 1000 * resumen['directo']['costo_usd_por_consulta'],
         1000 * resumen['rag_texto']['costo_usd_por_consulta'], 1000 * resumen['rag_visual']['costo_usd_por_consulta']],
        [COLOR['directo'], '#84b9f3', COLOR['rag_texto'], COLOR['rag_visual']], 2,
    )
    latencia.set_title('Latencia mediana\n(segundos)')
    _barras_horizontales(latencia, nombres, [resumen[s]['latencia_mediana_s'] for s in SISTEMAS], colores, 2)
    guardar(figura, 'costo_y_latencia')


def figura_entropia() -> None:
    resultados = leer_json(ARCHIVO_ENTROPIA, {})
    preguntas = leer_json(PREGUNTAS_DE_VIGENCIA, [])
    figura, ejes = lienzo(7.6, 3.3)
    for fila, pregunta in enumerate(preguntas):
        for columna, configuracion in enumerate(CONFIGURACIONES):
            fondo, texto = CLASE[resultados[f"{pregunta['id']}|{configuracion}"]['clase']]
            ejes.add_patch(Rectangle((columna + 0.03, fila + 0.05), 0.94, 0.9, facecolor=fondo, edgecolor='none'))
            ejes.text(columna + 0.5, fila + 0.5, texto, ha='center', va='center', fontsize=8)
    ejes.set_xlim(0, len(CONFIGURACIONES))
    ejes.set_ylim(len(preguntas), 0)
    ejes.set_xticks([c + 0.5 for c in range(len(CONFIGURACIONES))], [CONFIGURACION[c] for c in CONFIGURACIONES])
    ejes.set_yticks([f + 0.5 for f in range(len(preguntas))], [PREGUNTA_DE_VIGENCIA[p['id']] for p in preguntas])
    ejes.xaxis.tick_top()
    ejes.tick_params(colors=TINTA)
    for lado in ejes.spines.values():
        lado.set_visible(False)
    guardar(figura, 'entropia_poc')


def figura_demanda_semanal() -> None:
    with sqlite3.connect(BODEGA) as bodega:
        filas = bodega.execute(
            f"""SELECT periodo, semana_del_periodo, count(*) FROM v_reservas
                WHERE servicio = 'IP' AND periodo IN ({','.join('?' * len(SEMESTRES_DE_DEMANDA))})
                GROUP BY 1, 2""", SEMESTRES_DE_DEMANDA,
        ).fetchall()
    figura, paneles = lienzo(7.2, 4.6, len(SEMESTRES_DE_DEMANDA), 1, sharex=True, gridspec_kw={'hspace': 0.35})
    for panel, periodo in zip(paneles, SEMESTRES_DE_DEMANDA, strict=True):
        semanas = {semana: reservas for p, semana, reservas in filas if p == periodo}
        panel.bar(list(semanas), list(semanas.values()), 0.8, color=COLOR['directo'])
        panel.set_ylim(0, 700)
        panel.set_yticks([0, 300, 600])
        panel.yaxis.grid(True)
        panel.set_axisbelow(True)
        panel.spines['left'].set_visible(False)
        panel.text(0.005, 0.86, periodo_legible(periodo), transform=panel.transAxes, fontweight='bold', fontsize=9)
    paneles[-1].set_xticks(range(1, 19))
    paneles[-1].set_xlabel('Semana del semestre (1 = semana de la primera reserva)')
    figura.supylabel('Reservas de tutoría de IP por semana', fontsize=9, color=TINTA_SECUNDARIA, x=0.04)
    guardar(figura, 'demanda_semanal')


def figura_palabras_por_ingesta() -> None:
    """Palabras recuperadas por nivel con cada ingesta, sobre los documentos vigentes."""
    with psycopg.connect(DATABASE_URL) as conexion:
        filas = conexion.execute(
            """SELECT coalesce('Nivel ' || d.nivel, 'Programa'), f.coleccion, sum(f.palabras)
               FROM fragmentos f JOIN documentos d ON d.id = f.documento_id
               WHERE d.vigente GROUP BY 1, 2"""
        ).fetchall()
    grupos = ['Programa', 'Nivel 1', 'Nivel 2', 'Nivel 3', 'Nivel 4']
    palabras = {(grupo, coleccion): total for grupo, coleccion, total in filas}
    figura, ejes = lienzo(7.2, 2.7)
    ancho = 0.38
    for desplazamiento, (coleccion, sistema) in enumerate((('texto', 'rag_texto'), ('visual', 'rag_visual'))):
        for posicion, grupo in enumerate(grupos):
            x = posicion + (desplazamiento - 0.5) * ancho
            valor = palabras[(grupo, coleccion)]
            ejes.bar(x, valor, ancho - 0.03, color=COLOR[sistema],
                     label=('Capa de texto del PDF' if coleccion == 'texto' else 'Transcripción con visión') if posicion == 0 else None)
            ejes.text(x, valor + 150, numero(valor), ha='center', va='bottom', fontsize=7.5)
    ejes.set_xticks(range(len(grupos)), grupos)
    ejes.set_ylabel('Palabras indexadas')
    ejes.set_ylim(0, max(palabras.values()) * 1.1)
    ejes.set_yticks([])
    ejes.spines['left'].set_visible(False)
    ejes.tick_params(axis='x', colors=TINTA)
    ejes.legend(frameon=False, ncols=2, loc='lower left', bbox_to_anchor=(-0.02, 1.0), columnspacing=1.2, handlelength=1.2)
    guardar(figura, 'palabras_por_ingesta')


def main() -> None:
    for figura in (figura_exactitud, figura_costo_y_latencia, figura_entropia, figura_demanda_semanal, figura_palabras_por_ingesta):
        figura()
        print(f'  {figura.__name__}')


if __name__ == '__main__':
    main()
