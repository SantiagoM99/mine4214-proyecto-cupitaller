"""Ejecuta el pipeline completo de Bronze a Gold y el tablero, en orden.

    python3 src/main.py                    # datos reales en data/bronce/Bookeau/
    python3 src/main.py --dummy            # datos ficticios de data/bronce/dummy/
    python3 src/main.py --desde limpiar    # retoma desde un paso
    python3 src/main.py --solo gold tablero
    python3 src/main.py --lista            # muestra los pasos

Con --dummy los Excel se leen de data/bronce/dummy/ (se generan si faltan) y el resto del flujo es
el mismo: escribe en data/plata, data/oro y docs/, por lo que reemplaza los resultados que hubiera.
Para volver a los datos reales, basta ejecutar python3 src/main.py sin --dummy.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
DUMMY = ROOT / 'data/bronce/dummy'

# (nombre corto, script, descripción)
PASOS = [
    ('caracterizar', 'caracterizar_bookeau.py', 'perfilamiento de Bronze'),
    ('documentar', 'documentar_caracterizacion.py', 'diccionario y documento de caracterización'),
    ('preparar', 'preparar_analisis_bookeau.py', 'evidencia de calidad para los análisis'),
    ('limpiar', 'limpiar_bookeau.py', 'Bronze → Silver'),
    ('comprobar', 'comprobar_estados_encuestas.py', 'cruce estados de reserva × encuestas'),
    ('gold', 'construir_gold_bookeau.py', 'Silver → Gold + controles'),
    ('tablero', 'generar_tablero_bookeau.py', 'tablero interactivo'),
]
NOMBRES = [p[0] for p in PASOS]


def seleccionar(args):
    if args.solo:
        return [p for p in PASOS if p[0] in args.solo]
    if args.desde:
        return PASOS[NOMBRES.index(args.desde):]
    return PASOS


def hay_excel(carpeta: Path) -> bool:
    return carpeta.is_dir() and any(carpeta.rglob('*.xlsx'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dummy', action='store_true', help='usar datos ficticios en lugar de los reales')
    ap.add_argument('--regenerar-dummy', action='store_true', help='con --dummy, vuelve a generar los datos ficticios')
    grupo = ap.add_mutually_exclusive_group()
    grupo.add_argument('--desde', choices=NOMBRES, help='empezar en este paso')
    grupo.add_argument('--solo', nargs='+', choices=NOMBRES, metavar='PASO', help='ejecutar solo estos pasos')
    ap.add_argument('--lista', action='store_true', help='mostrar los pasos y salir')
    args = ap.parse_args()

    if args.lista:
        for i, (nombre, script, descripcion) in enumerate(PASOS, 1):
            print(f'{i}. {nombre:<13} {script:<34} {descripcion}')
        return 0

    env = os.environ.copy()
    if args.dummy:
        if args.regenerar_dummy or not hay_excel(DUMMY):
            print('== Generando datos ficticios', flush=True)
            subprocess.run([sys.executable, str(SRC / 'generar_datos_dummy.py')], check=True)
        env['CUPITALLER_FUENTE'] = 'data/bronce/dummy'
        print('Modo dummy: se leen los Excel de data/bronce/dummy/; Silver, Gold y docs se reemplazan.')
    else:
        env.pop('CUPITALLER_FUENTE', None)
        if not hay_excel(ROOT / 'data/bronce/Bookeau'):
            print('No hay libros de Excel en data/bronce/Bookeau/. Copia allí los datos reales '
                  '(ver data/README.md) o ejecuta con --dummy para probar con datos ficticios.', file=sys.stderr)
            return 1

    pasos = seleccionar(args)
    inicio = time.time()
    for i, (nombre, script, descripcion) in enumerate(pasos, 1):
        print(f'\n== [{i}/{len(pasos)}] {nombre}: {descripcion}', flush=True)
        t = time.time()
        resultado = subprocess.run([sys.executable, str(SRC / script)], cwd=ROOT, env=env)
        if resultado.returncode:
            print(f'\nFalló el paso «{nombre}» (código {resultado.returncode}). '
                  f'Corrige el problema y retoma con: python3 src/main.py {"--dummy " if args.dummy else ""}--desde {nombre}', file=sys.stderr)
            return resultado.returncode
        print(f'-- {nombre} terminó en {time.time() - t:.1f} s', flush=True)
    print(f'\nPipeline completo en {time.time() - inicio:.1f} s.')
    print('Silver: data/plata · Gold: data/oro · Tablero: docs/entregables/tablero_bookeau.html')
    return 0


if __name__ == '__main__':
    sys.exit(main())
