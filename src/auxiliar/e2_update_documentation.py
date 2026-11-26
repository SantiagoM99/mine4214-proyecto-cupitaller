"""Actualiza todo el material del informe y del póster de la Entrega 2 en un solo paso.

    python3 src/auxiliar/e2_update_documentation.py                   # los cuatro, en orden
    python3 src/auxiliar/e2_update_documentation.py --solo temas modelo

Pasos, en el orden en que se ejecutan:
    temas    e2_temas_por_nivel.py     tabla del informe (artifacts/entrega2/tablas/)
    modelo   e2_modelo_dimensional.py  diagrama del modelo para el póster; se detiene si no coincide con el DDL
    figuras  e2_figuras.py             gráficas del informe (artifacts/entrega2/figuras/)
    poster   e2_figuras_poster.py      gráficas y recortes del póster (artifacts/entrega2/poster/)

`temas` y `modelo` solo usan el catálogo versionado y el Gold de la Entrega 1, así que corren sin documentos,
llave ni Postgres. `figuras` y `poster` además necesitan los resultados de `evaluar` y `entropia` (y Postgres y
las páginas renderizadas, respectivamente). Se detiene en el primer paso que falla.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PASOS = {
    'temas': 'e2_temas_por_nivel.py',
    'modelo': 'e2_modelo_dimensional.py',
    'figuras': 'e2_figuras.py',
    'poster': 'e2_figuras_poster.py',
}


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumentos.add_argument('--solo', nargs='+', choices=list(PASOS), metavar='PASO', help='ejecutar solo estos pasos')
    for nombre in argumentos.parse_args().solo or PASOS:
        print(f'   · {nombre}', flush=True)
        inicio = time.perf_counter()
        if subprocess.run([sys.executable, str(AQUI / PASOS[nombre])]).returncode != 0:
            sys.exit(f'El paso «{nombre}» de update_documentation falló. Corrige el problema y repite con: '
                     f'python3 src/auxiliar/e2_update_documentation.py --solo {nombre}')
        print(f'   · {nombre} terminó en {time.perf_counter() - inicio:.1f} s', flush=True)


if __name__ == '__main__':
    main()
