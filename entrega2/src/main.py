"""Ejecuta el flujo de la Entrega 2 de principio a fin, o los pasos que se indiquen.

    python3 src/main.py                 # todos los pasos, en orden
    python3 src/main.py --lista         # lista los pasos
    python3 src/main.py --desde indexar # retoma desde un paso
    python3 src/main.py --solo evaluar

Antes de empezar: `scripts/postgres.sh iniciar` y la llave de OpenAI (ver README).
Los pasos que llaman al modelo guardan sus resultados y no repiten lo ya hecho.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent

PASOS = [
    ('catalogo', 'catalogo.py', 'etiqueta cada documento con semestre, vigencia y nivel'),
    ('transcribir', 'transcribir.py', 'ingesta visual: una transcripción por página'),
    ('indexar', 'indexar.py', 'chunking, embeddings y carga en pgvector (colecciones texto y visual)'),
    ('bodega', 'bodega.py', 'copia el Gold de la Entrega 1 y crea las vistas del agente'),
    ('evaluar', 'evaluar.py', 'prompting directo, RAG de texto y RAG visual sobre el banco de preguntas'),
    ('entropia', 'poc_entropia.py', 'prueba de concepto con documentos desactualizados'),
    ('agente', 'casos_agente.py', 'casos del agente híbrido (RAG + SQL)'),
    ('figuras', 'figuras.py', 'gráficas del informe'),
    ('temas', 'temas_por_nivel.py', 'clases de 2026-20 con y sin versión en el material de 2020-21'),
    ('poster', 'figuras_poster.py', 'gráficas y recortes de documentos del póster'),
    ('modelo', 'modelo_dimensional.py', 'diagrama del modelo dimensional, comprobado contra el DDL'),
]
NOMBRES = [nombre for nombre, _, _ in PASOS]


def seleccionar(opciones: argparse.Namespace) -> list[tuple[str, str, str]]:
    if opciones.solo:
        return [paso for paso in PASOS if paso[0] in opciones.solo]
    if opciones.desde:
        return PASOS[NOMBRES.index(opciones.desde):]
    return PASOS


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    grupo = argumentos.add_mutually_exclusive_group()
    grupo.add_argument('--desde', choices=NOMBRES, help='empezar en este paso')
    grupo.add_argument('--solo', nargs='+', choices=NOMBRES, metavar='PASO', help='ejecutar solo estos pasos')
    argumentos.add_argument('--lista', action='store_true', help='mostrar los pasos y salir')
    opciones = argumentos.parse_args()
    if opciones.lista:
        for nombre, script, descripcion in PASOS:
            print(f'{nombre:<12} {script:<18} {descripcion}')
        return
    for nombre, script, descripcion in seleccionar(opciones):
        print(f'== {nombre}: {descripcion}')
        inicio = time.perf_counter()
        if subprocess.run([sys.executable, str(SRC / script)]).returncode != 0:
            sys.exit(f'El paso «{nombre}» falló. Corrige el problema y retoma con: python3 src/main.py --desde {nombre}')
        print(f'-- {nombre} terminó en {time.perf_counter() - inicio:.1f} s\n')


if __name__ == '__main__':
    main()
