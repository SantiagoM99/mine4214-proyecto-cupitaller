"""Ejecuta el agente sobre los casos de data/evaluacion/preguntas_agente.json y guarda la traza de cada uno.

    python3 src/casos_agente.py [--rehacer]
"""

import argparse
from dataclasses import asdict

from agente import preguntar
from base_vectorial import conectar
from config import DIR_RESULTADOS, PREGUNTAS
from evaluar import guardar_json, leer_json
from llm import cliente

CASOS = PREGUNTAS.with_name('preguntas_agente.json')
ARCHIVO = DIR_RESULTADOS / 'agente' / 'casos.json'


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumentos.add_argument('--rehacer', action='store_true', help='descarta las trazas guardadas')
    if argumentos.parse_args().rehacer:
        ARCHIVO.unlink(missing_ok=True)
    trazas = leer_json(ARCHIVO, {})
    api = cliente()
    with conectar() as conexion:
        for caso in leer_json(CASOS, []):
            if caso['id'] not in trazas:
                trazas[caso['id']] = {**caso, **asdict(preguntar(api, conexion, caso['pregunta']))}
                guardar_json(ARCHIVO, trazas)
            traza = trazas[caso['id']]
            herramientas = ', '.join(paso['herramienta'] for paso in traza['pasos'])
            print(f"{caso['id']} ({caso['tipo']}): {len(traza['pasos'])} pasos [{herramientas}] · {traza['uso']}")


if __name__ == '__main__':
    main()
