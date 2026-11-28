"""Experimento con un modelo de pesos abiertos (Qwen3 30B-A3B en Ollama) en lugar de gpt-6-luna.

Tres pruebas, con el mismo código de la evaluación y del agente:
  rag      el banco a mano (26 preguntas) con RAG visual; califica gpt-6-sol, como en evaluar.py
  juez     Qwen3 como juez de las respuestas ya calificadas por gpt-6-sol: acuerdo entre jueces
  agente   los casos del agente; una rúbrica de gpt-6-sol califica cada traza
  rubrica  vuelve a calificar las trazas guardadas del agente

Se prueban dos variantes del mismo modelo: la instruct (responde sin razonar) y la que
razona antes de responder. gpt-6-luna se toma de las corridas ya guardadas.

El enfoque directo no se prueba: su prompt tiene 103 mil tokens y la caché de atención
de ese contexto (unos 10 GB) más los pesos (18 GB) no caben en los 32 GB del equipo.

    python3 src/entrega2/exp_modelo_abierto.py [rag] [juez] [agente] [rubrica]
"""

import argparse
import json
import statistics
from collections import Counter
from dataclasses import asdict

from agente import preguntar
from base_vectorial import conectar, embedding_de_pregunta
from bodega import descripcion
from config import DIR_RESULTADOS, MODELO_JUEZ, MODELO_LOCAL, MODELO_LOCAL_RAZONADOR, PREGUNTAS
from enfoques import responder_rag
from juez import FORMATO, INSTRUCCIONES as INSTRUCCIONES_JUEZ, juzgar
from llm import cliente, cliente_local, generar

DIR_EXPERIMENTOS = DIR_RESULTADOS / 'experimentos'
ARCHIVO = DIR_EXPERIMENTOS / 'modelo_abierto.json'
ARCHIVO_RESUMEN = DIR_EXPERIMENTOS / 'modelo_abierto_resumen.json'
EVALUACION = DIR_RESULTADOS / 'evaluacion'
CASOS_AGENTE = PREGUNTAS.with_name('preguntas_agente.json')
TRAZAS_GPT = DIR_RESULTADOS / 'agente' / 'casos.json'
MODELOS_LOCALES = {'qwen3-instruct': MODELO_LOCAL, 'qwen3-razonador': MODELO_LOCAL_RAZONADOR}
# Con 3.000 el juez no veía el 4.º y 5.º fragmento de una búsqueda (unos 5.000 caracteres) y marcaba
# como inventadas citas que sí estaban en la salida, como en el caso 1.
MAX_CARACTERES_POR_HERRAMIENTA = 12000

RUBRICA = """Calificas la respuesta final de un agente de análisis que usa herramientas (búsqueda en documentos del curso, SQL sobre una bodega de datos y reservas del día).
Recibes la pregunta, la descripción de la bodega que el agente tenía en sus instrucciones, lo que devolvió cada herramienta y la respuesta final. Califica tres criterios de 0 a 2:

- fundamentada: 2 si toda cifra y afirmación de la respuesta aparece en las salidas de las herramientas o en la descripción de la bodega; 1 si hay alguna afirmación sin respaldo menor; 0 si inventa cifras o hechos.
- responde: 2 si responde la pregunta de forma completa; 1 si la responde a medias; 0 si no la responde.
- cita: 2 si cita el documento y la vista o tabla de donde sale cada dato; 1 si cita parcialmente; 0 si no cita.

Sé estricto con las cifras: compara cada número de la respuesta con las salidas."""

FORMATO_RUBRICA = {'format': {
    'type': 'json_schema', 'name': 'rubrica', 'strict': True,
    'schema': {
        'type': 'object',
        'properties': {
            'fundamentada': {'type': 'integer', 'enum': [0, 1, 2]},
            'responde': {'type': 'integer', 'enum': [0, 1, 2]},
            'cita': {'type': 'integer', 'enum': [0, 1, 2]},
            'motivo': {'type': 'string'},
        },
        'required': ['fundamentada', 'responde', 'cita', 'motivo'], 'additionalProperties': False,
    },
}}


def _leer(ruta, por_defecto):
    return json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else por_defecto


def _guardar(ruta, contenido) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prueba_rag(resultados: dict) -> None:
    preguntas = json.loads(PREGUNTAS.read_text(encoding='utf-8'))
    api, local = cliente(), cliente_local()
    embedding_de_pregunta('calentamiento')
    with conectar() as conexion:
        for nombre, modelo in MODELOS_LOCALES.items():
            for pregunta in preguntas:
                clave = f"rag|{pregunta['id']}|{nombre}"
                if clave in resultados:
                    continue
                r = responder_rag(local, conexion, pregunta['pregunta'], modelo=modelo)
                resultados[clave] = {'respuesta': r.respuesta, 'uso': r.uso, 'fuentes': r.fuentes,
                                     'veredicto': juzgar(api, pregunta, r.respuesta)}
                _guardar(ARCHIVO, resultados)
                print(f"{clave}: {resultados[clave]['veredicto']['veredicto']} en {r.uso['segundos']} s", flush=True)


def prueba_juez(resultados: dict) -> None:
    """Qwen3 instruct califica las respuestas de rag_texto y rag_visual que ya calificó gpt-6-sol."""
    preguntas = {p['id']: p for p in json.loads(PREGUNTAS.read_text(encoding='utf-8'))}
    respuestas = _leer(EVALUACION / 'respuestas.json', {})
    local = cliente_local()
    for clave, respuesta in respuestas.items():
        id_pregunta, sistema = clave.split('|')
        if sistema == 'directo' or f'juez|{clave}' in resultados:
            continue
        pregunta = preguntas[id_pregunta]
        caso = json.dumps({
            'pregunta': pregunta['pregunta'], 'respondible_con_los_documentos': pregunta['respondible'],
            'respuesta_esperada': pregunta['respuesta_esperada'], 'respuesta_del_asistente': respuesta['respuesta'],
        }, ensure_ascii=False, indent=2)
        crudo = generar(local, INSTRUCCIONES_JUEZ, caso, modelo=MODELO_LOCAL, text=FORMATO)
        resultados[f'juez|{clave}'] = {'veredicto': json.loads(crudo.texto), 'segundos': round(crudo.segundos, 2)}
        _guardar(ARCHIVO, resultados)


def _traza_para_rubrica(caso: dict, traza: dict) -> str:
    pasos = [{'herramienta': p['herramienta'], 'argumentos': p['argumentos'],
              'salida': p['resultado'][:MAX_CARACTERES_POR_HERRAMIENTA]} for p in traza['pasos']]
    return json.dumps({'pregunta': caso['pregunta'], 'descripcion_de_la_bodega': descripcion(),
                       'herramientas': pasos, 'respuesta_final': traza['respuesta']}, ensure_ascii=False, indent=2)


def prueba_agente(resultados: dict) -> None:
    casos = json.loads(CASOS_AGENTE.read_text(encoding='utf-8'))
    trazas_gpt = _leer(TRAZAS_GPT, {})
    api, local = cliente(), cliente_local()
    with conectar() as conexion:
        for caso in casos:
            for nombre, modelo in {'gpt-6-luna': None, **MODELOS_LOCALES}.items():
                clave = f"agente|{caso['id']}|{nombre}"
                if clave in resultados:
                    continue
                if modelo is None:
                    traza = trazas_gpt[caso['id']]
                else:
                    traza = asdict(preguntar(local, conexion, caso['pregunta'], modelo=modelo))
                rubrica = json.loads(generar(api, RUBRICA, _traza_para_rubrica(caso, traza), modelo=MODELO_JUEZ,
                                             text=FORMATO_RUBRICA).texto)
                resultados[clave] = {'traza': traza, 'rubrica': rubrica}
                _guardar(ARCHIVO, resultados)
                print(f"{clave}: {len(traza['pasos'])} pasos, {traza['uso'].get('segundos')} s, "
                      f"rúbrica {rubrica['fundamentada']}/{rubrica['responde']}/{rubrica['cita']}", flush=True)


def recalificar_agente(resultados: dict) -> None:
    """Vuelve a calificar las trazas guardadas del agente, sin volver a correr los modelos."""
    casos = {caso['id']: caso for caso in json.loads(CASOS_AGENTE.read_text(encoding='utf-8'))}
    api = cliente()
    for clave, registro in resultados.items():
        if clave.startswith('agente|'):
            caso = casos[clave.split('|')[1]]
            registro['rubrica'] = json.loads(generar(api, RUBRICA, _traza_para_rubrica(caso, registro['traza']),
                                                     modelo=MODELO_JUEZ, text=FORMATO_RUBRICA).texto)
            _guardar(ARCHIVO, resultados)
            print(f"{clave}: rúbrica {registro['rubrica']['fundamentada']}/{registro['rubrica']['responde']}/{registro['rubrica']['cita']}", flush=True)


def kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    observado = sum(x == y for x, y in zip(a, b, strict=True)) / n
    ca, cb = Counter(a), Counter(b)
    esperado = sum(ca[c] * cb[c] for c in set(a) | set(b)) / n**2
    return round((observado - esperado) / (1 - esperado), 3) if esperado < 1 else 1.0


def resumir(resultados: dict) -> dict:
    preguntas = json.loads(PREGUNTAS.read_text(encoding='utf-8'))
    respuestas_gpt = _leer(EVALUACION / 'respuestas.json', {})
    veredictos_gpt = _leer(EVALUACION / 'veredictos.json', {})
    resumen = {'rag': {}, 'juez': {}, 'agente': {}}

    filas = {'gpt-6-luna': [(veredictos_gpt[f"{p['id']}|rag_visual"], respuestas_gpt[f"{p['id']}|rag_visual"]['uso']) for p in preguntas]}
    for nombre in MODELOS_LOCALES:
        if all(f"rag|{p['id']}|{nombre}" in resultados for p in preguntas):
            filas[nombre] = [(resultados[f"rag|{p['id']}|{nombre}"]['veredicto'], resultados[f"rag|{p['id']}|{nombre}"]['uso']) for p in preguntas]
    for nombre, casos in filas.items():
        conteo = Counter(v['veredicto'] for v, _ in casos)
        resumen['rag'][nombre] = {
            'preguntas': len(casos), 'correctas': conteo['correcta'], 'parciales': conteo['parcial'],
            'incorrectas': conteo['incorrecta'], 'alucinaciones': sum(v['alucinacion'] for v, _ in casos),
            'latencia_mediana_s': round(statistics.median(u['segundos'] for _, u in casos), 2),
            'latencia_maxima_s': round(max(u['segundos'] for _, u in casos), 2),
            'tokens_salida_promedio': round(statistics.mean(u['tokens_salida'] for _, u in casos)),
        }

    pares = [(veredictos_gpt[c.removeprefix('juez|')]['veredicto'], r['veredicto']['veredicto'])
             for c, r in resultados.items() if c.startswith('juez|')]
    if pares:
        resumen['juez'] = {
            'respuestas': len(pares),
            'acuerdo_pct': round(100 * sum(a == b for a, b in pares) / len(pares), 1),
            'kappa_de_cohen': kappa([a for a, _ in pares], [b for _, b in pares]),
            'matriz_gpt_vs_qwen': dict(Counter(f'{a}->{b}' for a, b in pares)),
            'segundos_mediana': statistics.median(r['segundos'] for c, r in resultados.items() if c.startswith('juez|')),
        }

    for nombre in ['gpt-6-luna', *MODELOS_LOCALES]:
        del_modelo = [r for c, r in resultados.items() if c.startswith('agente|') and c.endswith(f'|{nombre}')]
        if del_modelo:
            resumen['agente'][nombre] = {
                'casos': len(del_modelo),
                **{criterio: sum(r['rubrica'][criterio] for r in del_modelo) for criterio in ('fundamentada', 'responde', 'cita')},
                'maximo_por_criterio': 2 * len(del_modelo),
                'pasos_promedio': round(statistics.mean(len(r['traza']['pasos']) for r in del_modelo), 1),
                'segundos_mediana': round(statistics.median(r['traza']['uso'].get('segundos', 0) for r in del_modelo), 1),
                'sin_respuesta': sum(r['traza']['respuesta'].startswith('El agente no llegó') for r in del_modelo),
            }
    _guardar(ARCHIVO_RESUMEN, resumen)
    return resumen


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumentos.add_argument('pruebas', nargs='*', default=['rag', 'juez', 'agente'])
    pruebas = argumentos.parse_args().pruebas
    resultados = _leer(ARCHIVO, {})
    for prueba in pruebas:
        {'rag': prueba_rag, 'juez': prueba_juez, 'agente': prueba_agente, 'rubrica': recalificar_agente}[prueba](resultados)
    print(json.dumps(resumir(resultados), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
