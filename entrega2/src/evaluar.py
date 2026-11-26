"""Evaluación de los enfoques sobre el banco de preguntas (data/evaluacion/preguntas.json).

Tres sistemas responden las mismas preguntas con los documentos vigentes:
  directo     prompting directo con todos los documentos transcritos en el prompt
  rag_texto   RAG sobre la capa de texto de los PDF
  rag_visual  RAG sobre las transcripciones con visión

    python3 src/evaluar.py              # responde lo que falte, califica y resume
    python3 src/evaluar.py --rehacer    # descarta respuestas y veredictos guardados

Las respuestas y los veredictos quedan en resultados/evaluacion/ y se reutilizan
entre ejecuciones, porque cada respuesta cuesta una llamada al modelo.
"""

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

from base_vectorial import conectar, embedding_de_pregunta
from catalogo import cargar_catalogo
from config import DIR_RESULTADOS, PREGUNTAS, costo_usd
from enfoques import Resultado, documentos_completos, responder_directo, responder_rag
from juez import juzgar
from llm import cliente

SISTEMAS = ('directo', 'rag_texto', 'rag_visual')
COLECCION_DE_RAG = {'rag_texto': 'texto', 'rag_visual': 'visual'}
K = 5
DIR_EVALUACION = DIR_RESULTADOS / 'evaluacion'
ARCHIVO_RESPUESTAS = DIR_EVALUACION / 'respuestas.json'
ARCHIVO_VEREDICTOS = DIR_EVALUACION / 'veredictos.json'
ARCHIVO_RESUMEN = DIR_EVALUACION / 'resumen.json'


def leer_json(ruta: Path, por_defecto):
    return json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else por_defecto


def guardar_json(ruta: Path, contenido) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _clave(pregunta: dict, sistema: str) -> str:
    return f"{pregunta['id']}|{sistema}"


def generar_respuestas(preguntas: list[dict]) -> dict:
    respuestas = leer_json(ARCHIVO_RESPUESTAS, {})
    api = cliente()
    corpus = documentos_completos([doc for doc in cargar_catalogo() if doc.vigente])
    # La primera llamada carga el modelo de embeddings en memoria (unos 2 s); se hace
    # antes de medir para que esa carga no cuente como latencia de la primera pregunta.
    embedding_de_pregunta('calentamiento')
    with conectar() as conexion:
        for sistema in SISTEMAS:
            for pregunta in preguntas:
                if _clave(pregunta, sistema) in respuestas:
                    continue
                if sistema == 'directo':
                    resultado: Resultado = responder_directo(api, pregunta['pregunta'], corpus)
                else:
                    resultado = responder_rag(api, conexion, pregunta['pregunta'], coleccion=COLECCION_DE_RAG[sistema], k=K)
                respuestas[_clave(pregunta, sistema)] = {
                    'respuesta': resultado.respuesta, 'uso': resultado.uso, 'fuentes': resultado.fuentes,
                }
                guardar_json(ARCHIVO_RESPUESTAS, respuestas)
            print(f'  {sistema}: {len(preguntas)} preguntas respondidas')
    return respuestas


def juzgar_respuestas(preguntas: list[dict], respuestas: dict) -> dict:
    veredictos = leer_json(ARCHIVO_VEREDICTOS, {})
    api = cliente()
    for pregunta in preguntas:
        for sistema in SISTEMAS:
            clave = _clave(pregunta, sistema)
            if clave not in veredictos:
                veredictos[clave] = juzgar(api, pregunta, respuestas[clave]['respuesta'])
                guardar_json(ARCHIVO_VEREDICTOS, veredictos)
    return veredictos


def recupero_la_fuente(pregunta: dict, fuentes: list[str]) -> bool | None:
    """True si se recuperó alguna fuente esperada; None si la pregunta no tiene fuente.

    Una fuente esperada sin `paginas` se cumple con cualquier página de ese documento.
    """
    if not pregunta['fuentes']:
        return None
    for fuente in pregunta['fuentes']:
        esperadas = {f"{fuente['clave']} p. {pagina}" for pagina in fuente.get('paginas', [])}
        if esperadas & set(fuentes) or (not esperadas and any(f.startswith(f"{fuente['clave']} p. ") for f in fuentes)):
            return True
    return False


def _porcentaje(parte: int, total: int) -> float:
    return round(100 * parte / total, 1) if total else 0.0


def resumir(preguntas: list[dict], respuestas: dict, veredictos: dict) -> dict:
    resumen = {}
    for sistema in SISTEMAS:
        casos = [(p, respuestas[_clave(p, sistema)], veredictos[_clave(p, sistema)]) for p in preguntas]
        usos = [respuesta['uso'] for _, respuesta, _ in casos]
        conteo = Counter(veredicto['veredicto'] for _, _, veredicto in casos)
        aciertos = [
            acierto for pregunta, respuesta, _ in casos
            if sistema != 'directo' and (acierto := recupero_la_fuente(pregunta, respuesta['fuentes'])) is not None
        ]
        por_categoria = {}
        for categoria in sorted({p['categoria'] for p in preguntas}):
            del_grupo = [veredicto for pregunta, _, veredicto in casos if pregunta['categoria'] == categoria]
            por_categoria[categoria] = {
                'preguntas': len(del_grupo),
                'correctas': sum(v['veredicto'] == 'correcta' for v in del_grupo),
            }
        resumen[sistema] = {
            'preguntas': len(casos),
            'correctas_pct': _porcentaje(conteo['correcta'], len(casos)),
            'parciales_pct': _porcentaje(conteo['parcial'], len(casos)),
            'incorrectas_pct': _porcentaje(conteo['incorrecta'], len(casos)),
            'alucinaciones_pct': _porcentaje(sum(v['alucinacion'] for _, _, v in casos), len(casos)),
            'recuperacion_k5_pct': _porcentaje(sum(aciertos), len(aciertos)) if aciertos else None,
            'tokens_entrada_promedio': round(statistics.mean(u['tokens_entrada'] for u in usos)),
            'tokens_en_cache_promedio': round(statistics.mean(u['tokens_en_cache'] for u in usos)),
            'consultas_con_lectura_de_cache': sum(u['tokens_en_cache'] > 0 for u in usos),
            'tokens_salida_promedio': round(statistics.mean(u['tokens_salida'] for u in usos)),
            'latencia_mediana_s': round(statistics.median(u['segundos'] for u in usos), 2),
            'latencia_maxima_s': round(max(u['segundos'] for u in usos), 2),
            'costo_usd_por_consulta': round(statistics.mean(costo_usd(u) for u in usos), 6),
            'costo_usd_por_consulta_sin_cache': round(
                statistics.mean(costo_usd({**u, 'tokens_en_cache': 0, 'tokens_escritos_en_cache': 0}) for u in usos), 6),
            'por_categoria': por_categoria,
        }
    guardar_json(ARCHIVO_RESUMEN, resumen)
    return resumen


def imprimir(resumen: dict) -> None:
    filas = [
        ('correctas %', 'correctas_pct'), ('parciales %', 'parciales_pct'), ('incorrectas %', 'incorrectas_pct'),
        ('alucinaciones %', 'alucinaciones_pct'), ('recuperación@5 %', 'recuperacion_k5_pct'),
        ('tokens de entrada', 'tokens_entrada_promedio'), ('  leídos de caché', 'tokens_en_cache_promedio'),
        ('consultas con caché', 'consultas_con_lectura_de_cache'),
        ('tokens de salida', 'tokens_salida_promedio'), ('latencia mediana (s)', 'latencia_mediana_s'),
        ('latencia máxima (s)', 'latencia_maxima_s'), ('USD por consulta', 'costo_usd_por_consulta'),
        ('USD sin caché', 'costo_usd_por_consulta_sin_cache'),
    ]
    print(f'{"":<22}' + ''.join(f'{sistema:>14}' for sistema in SISTEMAS))
    for etiqueta, campo in filas:
        valores = [resumen[sistema][campo] for sistema in SISTEMAS]
        print(f'{etiqueta:<22}' + ''.join(f'{"—" if valor is None else valor:>14}' for valor in valores))


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumentos.add_argument('--rehacer', action='store_true', help='descarta las respuestas y los veredictos guardados')
    if argumentos.parse_args().rehacer:
        ARCHIVO_RESPUESTAS.unlink(missing_ok=True)
        ARCHIVO_VEREDICTOS.unlink(missing_ok=True)
    preguntas = leer_json(PREGUNTAS, None)
    if preguntas is None:
        raise FileNotFoundError(f'Falta el banco de preguntas: {PREGUNTAS}')
    respuestas = generar_respuestas(preguntas)
    veredictos = juzgar_respuestas(preguntas, respuestas)
    imprimir(resumir(preguntas, respuestas, veredictos))


if __name__ == '__main__':
    main()
