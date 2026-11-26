"""Entrega 2: ejecuta el flujo de principio a fin, o los pasos que se indiquen.

    python3 src/main.py --entrega 2                 # todos los pasos, en orden
    python3 src/main.py --entrega 2 --lista         # lista los pasos
    python3 src/main.py --entrega 2 --desde indexar # retoma desde un paso
    python3 src/main.py --entrega 2 --solo evaluar

Antes de empezar: `scripts/e2_postgres.sh iniciar` y la llave de OpenAI (ver README).
Los pasos que llaman al modelo guardan sus resultados y no repiten lo ya hecho.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent

# update_documentation produce el material del informe y del póster (tabla, figuras y diagrama):
# no es lógica del proyecto y vive en src/auxiliar/. Sus cuatro partes se pueden correr por separado.
PASOS = [
    ('catalogo', 'catalogo.py', 'etiqueta cada documento con semestre, vigencia y nivel'),
    ('transcribir', 'transcribir.py', 'ingesta visual: una transcripción por página'),
    ('indexar', 'indexar.py', 'chunking, embeddings y carga en pgvector (colecciones texto y visual)'),
    ('bodega', 'bodega.py', 'copia el Gold de la Entrega 1 y crea las vistas del agente'),
    ('evaluar', 'evaluar.py', 'prompting directo, RAG de texto y RAG visual sobre el banco de preguntas'),
    ('entropia', 'poc_entropia.py', 'prueba de concepto con documentos desactualizados'),
    ('agente', 'casos_agente.py', 'casos del agente híbrido (RAG + SQL)'),
    ('update_documentation', '../auxiliar/e2_update_documentation.py', 'tabla, figuras y diagrama del informe y del póster'),
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
            print(f'{nombre:<12} {script:<42} {descripcion}')
        return
    for nombre, script, descripcion in seleccionar(opciones):
        print(f'== {nombre}: {descripcion}')
        inicio = time.perf_counter()
        if subprocess.run([sys.executable, str(SRC / script)]).returncode != 0:
            sys.exit(f'El paso «{nombre}» falló. Corrige el problema y retoma con: python3 src/main.py --entrega 2 --desde {nombre}')
        print(f'-- {nombre} terminó en {time.perf_counter() - inicio:.1f} s\n')


if __name__ == '__main__':
    main()
