"""Punto de entrada único del proyecto: ejecuta el flujo de la Entrega 1 o el de la Entrega 2.

    python3 src/main.py --dummy                     # Entrega 1 con datos ficticios
    python3 src/main.py                             # Entrega 1 con los datos reales
    python3 src/main.py --dummy --desde gold        # Entrega 1 desde un paso
    python3 src/main.py --entrega 2                 # Entrega 2 completa
    python3 src/main.py --entrega 2 --desde indexar
    python3 src/main.py --entrega 2 --lista

El resto de las opciones se pasan tal cual al orquestador de cada entrega:
src/entrega1/main.py (pipeline Bronze → Silver → Gold y tablero) o
src/entrega2/main.py (documentos, RAG, agente y evaluación).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
ORQUESTADORES = {'1': SRC / 'entrega1' / 'main.py', '2': SRC / 'entrega2' / 'main.py'}


def separar_entrega(argumentos: list[str]) -> tuple[str, list[str]]:
    """Quita --entrega N (o --entrega=N) de los argumentos; por defecto, la Entrega 1."""
    entrega, resto = '1', []
    iterador = iter(argumentos)
    for argumento in iterador:
        if argumento == '--entrega':
            entrega = next(iterador, '')
        elif argumento.startswith('--entrega='):
            entrega = argumento.split('=', 1)[1]
        else:
            resto.append(argumento)
    if entrega not in ORQUESTADORES:
        sys.exit(f'--entrega debe ser 1 o 2 (recibido: {entrega!r}).')
    return entrega, resto


def main() -> int:
    if sys.argv[1:2] in (['-h'], ['--help']):
        print(__doc__)
        return 0
    entrega, resto = separar_entrega(sys.argv[1:])
    return subprocess.run([sys.executable, str(ORQUESTADORES[entrega]), *resto]).returncode


if __name__ == '__main__':
    sys.exit(main())
