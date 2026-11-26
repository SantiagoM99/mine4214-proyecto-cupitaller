"""Qué clases de 2026-20 tienen una versión en el material de 2020-20 y 2021-10.

    python3 src/auxiliar/e2_temas_por_nivel.py

La correspondencia se declara aquí, clase por clase, a partir de los títulos de
sección de las transcripciones: una clase de 2026-20 tiene versión si el tema
principal de su título aparece como sección de una presentación vieja. Se comprueba
contra el catálogo y escribe la tabla del informe (artifacts/entrega2/tablas/tabla_temas_por_nivel.tex).

Del material viejo hay 12 presentaciones, no el curso completo: una clase sin
correspondencia está «sin versión en el material de 2020-21», lo que no prueba que
el tema sea nuevo.
"""

from dataclasses import dataclass, field

import sys
from pathlib import Path

# Código auxiliar (informe y póster): usa los módulos del núcleo de la Entrega 2.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'entrega2'))

from catalogo import Documento, cargar_catalogo
from config import ARTIFACTS, RAIZ

TABLA = ARTIFACTS / 'tablas' / 'tabla_temas_por_nivel.tex'
PERIODO_ACTUAL = '2026-20'
PERIODOS_ANTERIORES = {'2020-20', '2021-10'}

CORRESPONDENCIA = {
    '2026-20_n1_01_descubriendo-el-mundo-de-la-programacion': ['2021-10_c2_analisis-y-diseno-de-un-programa'],
    '2026-20_n1_02_valores-y-tipos-de-dato': ['2020-20_c3_variables-y-expresiones'],
    '2026-20_n1_03_declaracion-de-variables-instruccion-de-asignacion-y-tipado-dinamico': ['2020-20_c3_variables-y-expresiones'],
    '2026-20_n1_04_expresiones-operadores-aritmeticos-y-operaciones-sobre-strings': ['2020-20_c3_variables-y-expresiones'],
    '2026-20_n1_05_conversion-de-tipos': ['2020-20_c3_variables-y-expresiones', '2020-20_c4_funciones'],
    '2026-20_n1_06_funciones-de-python-matematicas-y-de-entrada-salida': ['2020-20_c4_funciones'],
    '2026-20_n1_07_funciones-y-variables-locales': ['2020-20_c4_funciones'],
    '2026-20_n1_09_estilo-de-programacion': [],
    '2026-20_n1_10_construccion-e-importacion-de-modulos': [],
    # Funciones (2020-20) ya tiene «Interfaz básica de un programa», «Input vs Parámetro» y
    # «Print vs Retorno»: solo la interfaz lee e imprime. Le falta llevarla a otro módulo.
    '2026-20_n1_11_separacion-entre-interfaz-de-usuario-y-logica-del-programa': ['2020-20_c4_funciones'],
    '2026-20_n2_02_booleanos-y-sus-operadores': ['2021-10_c7_instrucciones-condicionales'],
    '2026-20_n2_03_tablas-de-verdad-y-algebra-booleana': ['2021-10_c7_instrucciones-condicionales'],
    '2026-20_n2_04_condicionales': ['2021-10_c7_instrucciones-condicionales'],
    '2026-20_n2_05_leyes-de-de-morgan': ['2021-10_c7_instrucciones-condicionales'],
    '2026-20_n2_06_cadenas-de-caracteres': ['2021-10_c8_cadenas-de-caracteres'],
    '2026-20_n2_07_operaciones-sobre-cadenas-de-caracteres': ['2021-10_c8_cadenas-de-caracteres'],
    '2026-20_n2_08_diccionarios-operaciones-basicas': ['2021-10_c9_diccionarios'],
    '2026-20_n2_09_diccionarios-mutabilidad-borrado-de-datos-y-parametros-por-referencia': ['2021-10_c9_diccionarios'],
    '2026-20_n2_11_diccionarios-para-manejar-elementos-con-las-mismas-caracteristicas': [],
    '2026-20_n3_02_instrucciones-iterativas-while': ['2021-10_c10_instrucciones-ciclicas'],
    '2026-20_n3_03_uso-del-centinela': ['2021-10_c10_instrucciones-ciclicas'],
    # La clase presenta como nuevos la indexación, las subcadenas y la inmutabilidad de los
    # strings; en 2021-10 el índice y el corte [:] solo aparecen para listas, y Cadenas solo
    # tiene find().
    '2026-20_n3_04_mas-sobre-strings': [],
    '2026-20_n3_05_instrucciones-iterativas-for': ['2021-10_c10_instrucciones-ciclicas'],
    '2026-20_n3_06_introduccion-a-listas': ['2021-10_c11_listas'],
    '2026-20_n3_07_operaciones-sobre-listas': ['2021-10_c11_listas'],
    '2026-20_n3_08_patrones-de-recorrido': ['2021-10_c12_patrones-de-recorrido'],
    '2026-20_n3_09_recorrido-de-diccionarios': [],
    '2026-20_n3_10_manejo-de-archivos': ['2021-10_c13_manejo-de-archivos'],
    # Tuplas (2021-10, nivel 4) tiene la sección «Estructuras compuestas»; el diccionario de
    # diccionarios leído de un archivo era además el ejemplo de Manejo de archivos.
    '2026-20_n3_11_estructura-de-datos-compuestos': ['2021-10_1_tuplas', '2021-10_c13_manejo-de-archivos'],
    '2026-20_n4_02_tuplas': ['2021-10_1_tuplas'],
    '2026-20_n4_03_estructuras-de-datos-con-tuplas': ['2021-10_1_tuplas'],
    '2026-20_n4_04_matrices': ['2020-20_2_matrices'],
    '2026-20_n4_05_mas-sobre-matrices': ['2020-20_2_matrices'],
    '2026-20_n4_06_introduccion-a-librerias': [],
    '2026-20_n4_07_introduccion-a-visualizaciones-con-matplotlib': [],
    '2026-20_n4_08_pandas-series-y-operaciones-sobre-series': [],
    '2026-20_n4_09_dataframes': [],
    '2026-20_n4_10_visualizacion-con-pandas': [],
}

# Introducciones de nivel y clases de ejercicios: no presentan un tema propio.
EXCLUIDAS = {
    '2026-20_n1_08_ejercicios-de-funciones',
    '2026-20_n2_01_introduccion',
    '2026-20_n2_10_ejercicio-ocurrencias-de-cada-digito-en-un-numero-usando-diccionarios',
    '2026-20_n3_01_introduccion-al-modulo',
    '2026-20_n3_12_ejericicios',
    '2026-20_n4_01_introduccion',
}

NOMBRE_CORTO = {
    '2026-20_n1_09_estilo-de-programacion': 'estilo de programación',
    '2026-20_n1_10_construccion-e-importacion-de-modulos': 'módulos',
    '2026-20_n2_11_diccionarios-para-manejar-elementos-con-las-mismas-caracteristicas': 'diccionarios como registros',
    '2026-20_n3_04_mas-sobre-strings': 'índices de strings',
    '2026-20_n3_09_recorrido-de-diccionarios': 'recorrido de diccionarios',
    '2026-20_n4_06_introduccion-a-librerias': 'librerías',
    '2026-20_n4_07_introduccion-a-visualizaciones-con-matplotlib': 'matplotlib',
    '2026-20_n4_08_pandas-series-y-operaciones-sobre-series': 'pandas: series',
    '2026-20_n4_09_dataframes': 'DataFrames',
    '2026-20_n4_10_visualizacion-con-pandas': 'gráficas con pandas',
}


@dataclass
class Nivel:
    """Clases de 2026-20 de un nivel: títulos de las que tienen versión, nombres cortos de las que no."""
    nivel: int
    con_version: list[str] = field(default_factory=list)
    sin_version: list[str] = field(default_factory=list)


def _presentaciones(catalogo: list[Documento], periodos: set[str]) -> dict[str, Documento]:
    return {d.clave: d for d in catalogo if d.tipo == 'presentacion' and d.periodo in periodos}


def comprobar(catalogo: list[Documento] | None = None) -> None:
    catalogo = catalogo if catalogo is not None else cargar_catalogo()
    actuales = _presentaciones(catalogo, {PERIODO_ACTUAL})
    anteriores = _presentaciones(catalogo, PERIODOS_ANTERIORES)
    declaradas = set(CORRESPONDENCIA) | EXCLUIDAS
    if faltan := sorted(set(actuales) - declaradas):
        raise ValueError(f'Clases de {PERIODO_ACTUAL} sin clasificar: {faltan}')
    if sobran := sorted(declaradas - set(actuales)):
        raise ValueError(f'Claves que no son presentaciones de {PERIODO_ACTUAL}: {sobran}')
    if repetidas := sorted(set(CORRESPONDENCIA) & EXCLUIDAS):
        raise ValueError(f'Clases a la vez clasificadas y excluidas: {repetidas}')
    if desconocidas := sorted({v for viejas in CORRESPONDENCIA.values() for v in viejas} - set(anteriores)):
        raise ValueError(f'Versiones que no son presentaciones de 2020-20 o 2021-10: {desconocidas}')
    sin_nombre = sorted(clave for clave, viejas in CORRESPONDENCIA.items() if not viejas and clave not in NOMBRE_CORTO)
    if sin_nombre or set(NOMBRE_CORTO) - {clave for clave, viejas in CORRESPONDENCIA.items() if not viejas}:
        raise ValueError(f'NOMBRE_CORTO debe cubrir exactamente las clases sin versión; faltan {sin_nombre}')


def por_nivel(catalogo: list[Documento] | None = None) -> list[Nivel]:
    """Clases de 2026-20 de cada nivel, con y sin versión anterior, en orden de clase."""
    catalogo = catalogo if catalogo is not None else cargar_catalogo()
    comprobar(catalogo)
    actuales = _presentaciones(catalogo, {PERIODO_ACTUAL})
    niveles = {nivel: Nivel(nivel) for nivel in range(1, 5)}
    for clave in sorted(CORRESPONDENCIA, key=lambda c: (actuales[c].nivel, actuales[c].orden)):
        documento = actuales[clave]
        if CORRESPONDENCIA[clave]:
            niveles[documento.nivel].con_version.append(documento.titulo)
        else:
            niveles[documento.nivel].sin_version.append(NOMBRE_CORTO[clave])
    return list(niveles.values())


def _latex(texto: str) -> str:
    return texto.replace('&', r'\&').replace('_', r'\_').replace('%', r'\%')


def escribir_tabla(catalogo: list[Documento]) -> None:
    actuales = _presentaciones(catalogo, {PERIODO_ACTUAL})
    anteriores = _presentaciones(catalogo, PERIODOS_ANTERIORES)
    filas = []
    for clave in sorted(CORRESPONDENCIA, key=lambda c: (actuales[c].nivel, actuales[c].orden)):
        actual = actuales[clave]
        versiones = '; '.join(f'{anteriores[v].titulo} ({anteriores[v].periodo}, N{anteriores[v].nivel})' for v in CORRESPONDENCIA[clave])
        filas.append(f'{actual.nivel} & {_latex(actual.titulo)} & {_latex(versiones) if versiones else r"\textbf{sin versión}"} \\\\')
    TABLA.parent.mkdir(parents=True, exist_ok=True)
    TABLA.write_text(
        '\\begin{longtable}{>{\\raggedleft\\arraybackslash}p{0.04\\textwidth}>{\\raggedright\\arraybackslash}p{0.46\\textwidth}>{\\raggedright\\arraybackslash}p{0.42\\textwidth}}\n'
        '\\caption{Clases de 2026-20 y su versión en el material de 2020-21. Sin introducciones ni ejercicios.}\\label{tab:versiones} \\\\\n'
        '\\toprule\n\\textbf{N} & \\textbf{Clase de 2026-20} & \\textbf{Versión en el material de 2020-21} \\\\\n\\midrule\n\\endhead\n'
        + '\n'.join(filas) + '\n\\bottomrule\n\\end{longtable}\n',
        encoding='utf-8',
    )


def main() -> None:
    catalogo = cargar_catalogo()
    for nivel in por_nivel(catalogo):
        print(f'N{nivel.nivel}: {len(nivel.con_version)} con versión, {len(nivel.sin_version)} sin versión: {"; ".join(nivel.sin_version)}')
    print(f'{len(CORRESPONDENCIA)} clases clasificadas y {len(EXCLUIDAS)} excluidas de {len(_presentaciones(catalogo, {PERIODO_ACTUAL}))}')
    escribir_tabla(catalogo)
    print(f'{TABLA.relative_to(RAIZ)}')


if __name__ == '__main__':
    main()
