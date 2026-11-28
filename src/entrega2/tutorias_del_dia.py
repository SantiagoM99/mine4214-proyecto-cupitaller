"""R3 a escala: el agente prepara la tutoría de cada estudiante que reservó un día.

Por cada reserva se le hace al agente la pregunta de un monitor. La métrica cuenta las
presentaciones vigentes que la respuesta propone como temas: dentro del nivel (la del
curso o una anterior) o de un nivel posterior.

La salida con datos reales va a artifacts/entrega2/privado/, que no se versiona; por
consola y en resultados/experimentos solo quedan métricas agregadas. La bodega no
registra en qué nivel va el curso: lo indica el monitor (--nivel).

    python3 src/entrega2/tutorias_del_dia.py --demo --repeticiones 5    # Pepito, ficticio
    python3 src/entrega2/tutorias_del_dia.py --fecha 2026-02-09 --nivel 1
"""

import argparse
import json
import re
import statistics
from dataclasses import asdict

from agente import listar_presentaciones, preguntar
from base_vectorial import conectar
from config import ARTIFACTS, DIR_RESULTADOS, PERIODO_VIGENTE, costo_usd
from llm import cliente
from reservas import FECHA_DEMO, estudiantes_del_dia

DIR_PRIVADO = ARTIFACTS / 'privado'
DIR_EXPERIMENTOS = DIR_RESULTADOS / 'experimentos'
FUENTES_DE_RESERVAS = {'reservas_del_dia', 'temas_del_estudiante'}
FUENTES_DOCUMENTALES = {'buscar_documentos', 'listar_presentaciones'}


def pregunta_del_monitor(fecha: str, estudiante: dict, nivel: int) -> str:
    return (f"Soy monitor. El {fecha} tengo tutoría con {estudiante['estudiante']} a las {estudiante['hora']} "
            f"y el curso va en el Nivel {nivel}. ¿Qué temas preparo?")


def presentaciones_nombradas(respuesta: str) -> dict[int, list[str]]:
    """Presentaciones vigentes nombradas en los temas numerados de la respuesta, por nivel.

    Solo cuentan las líneas numeradas: el agente también nombra, fuera de la lista, lo que
    deja por fuera por ser de un nivel posterior. Las introducciones de nivel no cuentan:
    sus títulos («Introducción») aparecen dentro de cualquier frase.
    """
    texto = '\n'.join(linea for linea in respuesta.lower().splitlines() if re.match(r'\s*\d+[.)]', linea))
    return {nivel: [t for t in listar_presentaciones(PERIODO_VIGENTE, nivel)['presentaciones']
                    if not t.startswith('Introducción') and t.lower() in texto]
            for nivel in range(1, 5)}


def preparar(api, conexion, fecha: str, estudiante: dict, nivel: int) -> dict:
    traza = asdict(preguntar(api, conexion, pregunta_del_monitor(fecha, estudiante, nivel)))
    nombradas = presentaciones_nombradas(traza['respuesta'])
    return {
        'estudiante': estudiante['estudiante'], 'traza': traza,
        'herramientas': [p['herramienta'] for p in traza['pasos']],
        'dentro_del_nivel': sum(len(t) for n, t in nombradas.items() if n <= nivel),
        'de_un_nivel_posterior': sum(len(t) for n, t in nombradas.items() if n > nivel),
    }


def metricas(preparaciones: list[dict]) -> dict:
    return {
        'estudiantes': len(preparaciones),
        'pidieron_temas_del_estudiante': sum('temas_del_estudiante' in p['herramientas'] for p in preparaciones),
        'sin_respuesta_en_el_limite_de_pasos': sum(p['traza']['respuesta'].startswith('El agente no llegó') for p in preparaciones),
        'respondieron_con_lista_de_temas': sum(p['dentro_del_nivel'] + p['de_un_nivel_posterior'] > 0 for p in preparaciones),
        'cruzaron_reserva_y_documentos': sum(bool(set(p['herramientas']) & FUENTES_DE_RESERVAS)
                                             and bool(set(p['herramientas']) & FUENTES_DOCUMENTALES) for p in preparaciones),
        'presentaciones_dentro_del_nivel': sum(p['dentro_del_nivel'] for p in preparaciones),
        'presentaciones_de_un_nivel_posterior': sum(p['de_un_nivel_posterior'] for p in preparaciones),
        'pasos_mediana': statistics.median(len(p['herramientas']) for p in preparaciones),
        'segundos_mediana': statistics.median(p['traza']['uso']['segundos'] for p in preparaciones),
        'costo_total_usd': round(sum(costo_usd(p['traza']['uso']) for p in preparaciones), 4),
    }


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumentos.add_argument('--demo', action='store_true', help='estudiante ficticio; la salida se puede versionar')
    argumentos.add_argument('--fecha', default='2026-02-09')
    argumentos.add_argument('--nivel', type=int, default=1)
    argumentos.add_argument('--repeticiones', type=int, default=1, help='veces que se prepara cada estudiante')
    a = argumentos.parse_args()
    fecha, nivel = (FECHA_DEMO, 2) if a.demo else (a.fecha, a.nivel)
    api = cliente()
    with conectar() as conexion:
        preparaciones = []
        for estudiante in estudiantes_del_dia(fecha) * a.repeticiones:
            preparaciones.append(preparar(api, conexion, fecha, estudiante, nivel))
            print(f"{estudiante['estudiante']}: {len(preparaciones[-1]['herramientas'])} pasos", flush=True)
    resumen = metricas(preparaciones) | {'fecha': fecha, 'nivel': nivel}
    salida = DIR_EXPERIMENTOS / 'tutorias_demo.json' if a.demo else DIR_PRIVADO / f'tutorias_{fecha}_nivel{nivel}.json'
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps({**resumen, 'preparaciones': preparaciones}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not a.demo:
        (DIR_EXPERIMENTOS / f'tutorias_{fecha}_metricas.json').write_text(
            json.dumps(resumen, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(resumen, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
