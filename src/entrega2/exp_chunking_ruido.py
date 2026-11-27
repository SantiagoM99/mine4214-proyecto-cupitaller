"""Variabilidad entre corridas de la calidad de respuesta en el experimento de chunking.

El generador y el juez no son deterministas: la misma variante puede sacar una o dos
correctas de diferencia entre corridas. Este script repite la generación y el juicio de
algunas variantes para saber qué diferencia entre variantes supera ese ruido.

    python3 src/entrega2/exp_chunking_ruido.py
"""

import json

from exp_chunking import DIR_EXPERIMENTOS, VARIANTES, _guardar, _leer, construir, responder
from config import PREGUNTAS
from juez import juzgar
from llm import cliente

ARCHIVO = DIR_EXPERIMENTOS / 'chunking_ruido.json'
REPETICIONES = 3
A_REPETIR = ['pagina_200_palabras (producción)', 'pagina_450_tokens', 'fija_256_solape_25', 'pagina_con_vecina (solape de 1 página)']


def main() -> None:
    preguntas = json.loads(PREGUNTAS.read_text(encoding='utf-8'))
    resultados = _leer(ARCHIVO, {})
    api = cliente()
    for nombre in A_REPETIR:
        trozos, vectores = construir(VARIANTES[nombre])
        for corrida in range(REPETICIONES):
            for pregunta in preguntas:
                clave = f"{nombre}|{corrida}|{pregunta['id']}"
                if clave not in resultados:
                    texto, _ = responder(api, trozos, vectores, pregunta['pregunta'])
                    resultados[clave] = juzgar(api, pregunta, texto)['veredicto']
                    _guardar(ARCHIVO, resultados)
        correctas = [sum(resultados[f"{nombre}|{c}|{p['id']}"] == 'correcta' for p in preguntas) for c in range(REPETICIONES)]
        print(f'{nombre}: correctas por corrida {correctas}', flush=True)


if __name__ == '__main__':
    main()
