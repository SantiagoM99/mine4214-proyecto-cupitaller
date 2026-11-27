"""Experimento de chunking: compara estrategias de partición sobre las transcripciones vigentes.

Todas las variantes usan el mismo modelo de embeddings, el mismo k y la misma búsqueda
exacta por coseno (en memoria), para que la diferencia medida sea solo la del chunking.
La base vectorial de producción no se toca.

Medidas:
  recuperación@5 y MRR sobre el banco sintético (200 preguntas, una por página) y sobre
  el banco escrito a mano (22 preguntas con fuente); tamaño de los fragmentos en tokens,
  fragmentos que pasan los 512 tokens que lee e5-small, tokens de contexto que recibiría
  el modelo; y, con --respuestas, la calidad de la respuesta sobre el banco a mano
  (generación con gpt-6-luna y juez gpt-6-sol, igual que evaluar.py).

    python3 src/entrega2/exp_chunking.py [--respuestas]
"""

import argparse
import json
import statistics
from dataclasses import dataclass

import numpy as np

from base_vectorial import Fragmento, embedding_de_pregunta, embeddings_de_pasajes, modelo_de_embeddings
from catalogo import Documento, cargar_catalogo
from config import DIR_RESULTADOS, PREGUNTAS
from enfoques import CITA_RAG, REGLA_DE_VIGENCIA, REGLAS, contexto_de_fragmentos
from indexar import partir_por_lineas
from juez import juzgar
from llm import CACHE_EXPLICITA, cliente, generar
from transcribir import leer_transcripcion, paginas_del_documento

DIR_EXPERIMENTOS = DIR_RESULTADOS / 'experimentos'
ARCHIVO_RESULTADOS = DIR_EXPERIMENTOS / 'chunking.json'
ARCHIVO_RESPUESTAS = DIR_EXPERIMENTOS / 'chunking_respuestas.json'
K = 5
LIMITE_E5 = 512


@dataclass(frozen=True)
class Trozo:
    doc: Documento
    paginas: tuple[int, ...]
    contenido: str


def _tokenizador():
    return modelo_de_embeddings().tokenizer


def contar_tokens(texto: str) -> int:
    return len(_tokenizador()(texto, add_special_tokens=False)['input_ids'])


def _paginas_con_texto(doc: Documento) -> list[tuple[int, str]]:
    return [(p.numero, t) for p in paginas_del_documento(doc) if (t := leer_transcripcion(p).strip())]


# --- Estrategias ---------------------------------------------------------------------------

def por_pagina_palabras(doc: Documento) -> list[Trozo]:
    """La de producción: una página por fragmento, partida entre líneas si pasa de 200 palabras."""
    return [Trozo(doc, (n,), t) for n, texto in _paginas_con_texto(doc) for t in partir_por_lineas(texto)]


def por_pagina_tokens(doc: Documento, maximo: int = 450) -> list[Trozo]:
    """Una página por fragmento, partida entre líneas si pasa de `maximo` tokens (título incluido)."""
    disponibles = maximo - contar_tokens(doc.titulo) - 4
    trozos = []
    for n, texto in _paginas_con_texto(doc):
        actual, tokens_actual = [], 0
        for linea in texto.splitlines():
            tokens = contar_tokens(linea) + 1
            if actual and tokens_actual + tokens > disponibles:
                trozos.append(Trozo(doc, (n,), '\n'.join(actual).strip()))
                actual, tokens_actual = [], 0
            actual.append(linea)
            tokens_actual += tokens
        if actual:
            trozos.append(Trozo(doc, (n,), '\n'.join(actual).strip()))
    return [t for t in trozos if t.contenido]


def ventana_fija(doc: Documento, tamano: int, solape: float = 0.0) -> list[Trozo]:
    """Ventanas de `tamano` tokens sobre el documento entero, sin respetar páginas ni líneas."""
    paginas = _paginas_con_texto(doc)
    texto, inicio_de_pagina = '', []
    for n, t in paginas:
        inicio_de_pagina.append((len(texto), n))
        texto += t + '\n\n'
    codificado = _tokenizador()(texto, add_special_tokens=False, return_offsets_mapping=True)
    offsets = codificado['offset_mapping']
    paso = max(1, int(tamano * (1 - solape)))
    trozos = []
    for i in range(0, len(offsets), paso):
        ventana = offsets[i:i + tamano]
        desde, hasta = ventana[0][0], ventana[-1][1]
        cubiertas = tuple(n for j, (ini, n) in enumerate(inicio_de_pagina)
                          if ini < hasta and (inicio_de_pagina[j + 1][0] if j + 1 < len(inicio_de_pagina) else len(texto)) > desde)
        trozos.append(Trozo(doc, cubiertas, texto[desde:hasta].strip()))
        if i + tamano >= len(offsets):
            break
    return trozos


def pagina_con_vecina(doc: Documento) -> list[Trozo]:
    """Cada fragmento es una página más la siguiente: cada página aparece en dos fragmentos."""
    paginas = _paginas_con_texto(doc)
    return [Trozo(doc, tuple(n for n, _ in paginas[i:i + 2]), '\n\n'.join(t for _, t in paginas[i:i + 2]))
            for i in range(len(paginas))]


def semantico(doc: Documento, umbral: float = 0.85, maximo: int = 450) -> list[Trozo]:
    """Tamaño variable: une páginas consecutivas mientras sus embeddings se parezcan y quepan en `maximo` tokens."""
    paginas = _paginas_con_texto(doc)
    if not paginas:
        return []
    vectores = embeddings_de_pasajes([t for _, t in paginas])
    grupos, actual, tokens_actual = [], [0], contar_tokens(paginas[0][1])
    for i in range(1, len(paginas)):
        tokens = contar_tokens(paginas[i][1])
        if float(vectores[i] @ vectores[i - 1]) >= umbral and tokens_actual + tokens <= maximo:
            actual.append(i)
            tokens_actual += tokens
        else:
            grupos.append(actual)
            actual, tokens_actual = [i], tokens
    grupos.append(actual)
    trozos = []
    for grupo in grupos:
        texto = '\n\n'.join(paginas[i][1] for i in grupo)
        # Una página sola puede pasar del máximo: se parte entre líneas como en por_pagina_tokens.
        if len(grupo) == 1 and contar_tokens(texto) > maximo:
            trozos += [t for t in por_pagina_tokens(doc, maximo) if t.paginas == (paginas[grupo[0]][0],)]
        else:
            trozos.append(Trozo(doc, tuple(paginas[i][0] for i in grupo), texto))
    return trozos


VARIANTES = {
    'pagina_200_palabras (producción)': por_pagina_palabras,
    'pagina_450_tokens': por_pagina_tokens,
    'fija_128': lambda d: ventana_fija(d, 128),
    'fija_256': lambda d: ventana_fija(d, 256),
    'fija_512': lambda d: ventana_fija(d, 480),
    'fija_128_solape_25': lambda d: ventana_fija(d, 128, 0.25),
    'fija_256_solape_15': lambda d: ventana_fija(d, 256, 0.15),
    'fija_256_solape_25': lambda d: ventana_fija(d, 256, 0.25),
    'pagina_con_vecina (solape de 1 página)': pagina_con_vecina,
    'semantico_variable': semantico,
}


# --- Medición ------------------------------------------------------------------------------

def construir(variante) -> tuple[list[Trozo], np.ndarray]:
    trozos = [t for doc in cargar_catalogo() if doc.vigente for t in variante(doc)]
    vectores = embeddings_de_pasajes([f'{t.doc.titulo}\n{t.contenido}' for t in trozos])
    return trozos, vectores


def acierto(trozo: Trozo, pregunta: dict) -> bool:
    for fuente in pregunta['fuentes']:
        if trozo.doc.clave == fuente['clave'] and (not fuente.get('paginas') or set(trozo.paginas) & set(fuente['paginas'])):
            return True
    return False


def medir_recuperacion(trozos, vectores, preguntas, vectores_preguntas) -> dict:
    rangos = []
    for pregunta, q in zip(preguntas, vectores_preguntas, strict=True):
        orden = np.argsort(-(vectores @ q))[:K]
        rango = next((r for r, i in enumerate(orden, start=1) if acierto(trozos[i], pregunta)), None)
        rangos.append(rango)
    return {
        'preguntas': len(preguntas),
        'recuperacion_k5_pct': round(100 * sum(r is not None for r in rangos) / len(rangos), 1),
        'recuperacion_k1_pct': round(100 * sum(r == 1 for r in rangos) / len(rangos), 1),
        'mrr': round(statistics.mean(1 / r if r else 0 for r in rangos), 3),
        'rangos': rangos,
    }


def tokens_de_contexto(trozos, vectores, vectores_preguntas) -> float:
    return statistics.mean(
        sum(contar_tokens(trozos[i].contenido) for i in np.argsort(-(vectores @ q))[:K]) for q in vectores_preguntas)


def responder(api, trozos, vectores, pregunta: str) -> tuple[str, dict]:
    q = embedding_de_pregunta(pregunta)
    elegidos = [trozos[i] for i in np.argsort(-(vectores @ q))[:K]]
    fragmentos = [Fragmento(t.doc.clave, t.doc.titulo, t.doc.periodo, t.doc.vigente, t.doc.nivel, t.paginas[0], t.contenido, 0.0)
                  for t in elegidos]
    instrucciones = '\n'.join([REGLAS, REGLA_DE_VIGENCIA, CITA_RAG])
    entrada = f'Fuentes:\n{contexto_de_fragmentos(fragmentos, con_vigencia=True)}\n\nPregunta: {pregunta}'
    respuesta = generar(api, instrucciones, entrada, **CACHE_EXPLICITA)
    return respuesta.texto, respuesta.uso


def _leer(ruta, por_defecto):
    return json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else por_defecto


def _guardar(ruta, contenido) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argumentos.add_argument('--respuestas', action='store_true', help='genera y califica respuestas con el banco a mano')
    con_respuestas = argumentos.parse_args().respuestas

    a_mano = json.loads(PREGUNTAS.read_text(encoding='utf-8'))
    con_fuente = [p for p in a_mano if p['fuentes']]
    sinteticas = json.loads((DIR_EXPERIMENTOS / 'preguntas_sinteticas.json').read_text(encoding='utf-8'))
    q_sint = np.array([embedding_de_pregunta(p['pregunta']) for p in sinteticas])
    q_mano = np.array([embedding_de_pregunta(p['pregunta']) for p in con_fuente])

    resultados = _leer(ARCHIVO_RESULTADOS, {})
    respuestas = _leer(ARCHIVO_RESPUESTAS, {})
    api = cliente() if con_respuestas else None
    for nombre, variante in VARIANTES.items():
        trozos, vectores = construir(variante)
        tamanos = [contar_tokens(f'passage: {t.doc.titulo}\n{t.contenido}') + 2 for t in trozos]
        fila = {
            'fragmentos': len(trozos),
            'tokens_mediana': statistics.median(tamanos),
            'tokens_max': max(tamanos),
            'fragmentos_truncados_por_e5': sum(n > LIMITE_E5 for n in tamanos),
            'paginas_por_fragmento': round(statistics.mean(len(t.paginas) for t in trozos), 2),
            'tokens_de_contexto_top5': round(tokens_de_contexto(trozos, vectores, q_sint)),
            'sinteticas': medir_recuperacion(trozos, vectores, sinteticas, q_sint),
            'a_mano': medir_recuperacion(trozos, vectores, con_fuente, q_mano),
        }
        if con_respuestas:
            for pregunta in a_mano:
                clave = f"{pregunta['id']}|{nombre}"
                if clave not in respuestas:
                    texto, uso = responder(api, trozos, vectores, pregunta['pregunta'])
                    respuestas[clave] = {'respuesta': texto, 'uso': uso, 'veredicto': juzgar(api, pregunta, texto)}
                    _guardar(ARCHIVO_RESPUESTAS, respuestas)
            veredictos = [respuestas[f"{p['id']}|{nombre}"]['veredicto'] for p in a_mano]
            fila['respuestas'] = {
                'preguntas': len(veredictos),
                'correctas': sum(v['veredicto'] == 'correcta' for v in veredictos),
                'parciales': sum(v['veredicto'] == 'parcial' for v in veredictos),
                'alucinaciones': sum(v['alucinacion'] for v in veredictos),
                'tokens_entrada_promedio': round(statistics.mean(respuestas[f"{p['id']}|{nombre}"]['uso']['tokens_entrada'] for p in a_mano)),
            }
        resultados[nombre] = fila
        _guardar(ARCHIVO_RESULTADOS, resultados)
        s, m = fila['sinteticas'], fila['a_mano']
        extra = f" | correctas {fila['respuestas']['correctas']}/{fila['respuestas']['preguntas']}" if con_respuestas else ''
        print(f"{nombre:<40} n={fila['fragmentos']:>4} med={fila['tokens_mediana']:>5} trunc={fila['fragmentos_truncados_por_e5']:>3} "
              f"ctx={fila['tokens_de_contexto_top5']:>5} | sint R@5 {s['recuperacion_k5_pct']:>5} MRR {s['mrr']:.3f} "
              f"| mano R@5 {m['recuperacion_k5_pct']:>5}{extra}")


if __name__ == '__main__':
    main()
