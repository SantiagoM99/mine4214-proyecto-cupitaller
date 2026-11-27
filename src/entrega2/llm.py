"""Llamadas al modelo generativo con el registro de tokens y tiempo que usa la evaluación."""

import base64
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from config import ARCHIVO_LLAVE, MODELO_LLM, URL_OLLAMA


@dataclass(frozen=True)
class Respuesta:
    texto: str
    tokens_entrada: int
    tokens_en_cache: int
    tokens_escritos_en_cache: int
    tokens_salida: int
    segundos: float
    crudo: Any = None

    @property
    def uso(self) -> dict[str, float]:
        return {
            'tokens_entrada': self.tokens_entrada, 'tokens_en_cache': self.tokens_en_cache,
            'tokens_escritos_en_cache': self.tokens_escritos_en_cache,
            'tokens_salida': self.tokens_salida, 'segundos': round(self.segundos, 2),
        }


def es_local(modelo: str) -> bool:
    """Los modelos de pesos abiertos corren en Ollama, que expone la misma API Responses."""
    return modelo.startswith('qwen3')


def cliente_local() -> OpenAI:
    return OpenAI(base_url=URL_OLLAMA, api_key='ollama', timeout=900)


def cliente() -> OpenAI:
    if not ARCHIVO_LLAVE.exists():
        raise FileNotFoundError(f'No se encontró la llave de OpenAI en {ARCHIVO_LLAVE}. Define OPENAI_API_KEY_FILE en .env.')
    return OpenAI(api_key=ARCHIVO_LLAVE.read_text(encoding='utf-8').strip(), max_retries=6, timeout=300)


# En el modo por defecto el proveedor escribe en caché todo prompt de más de 1.024 tokens
# y cobra esa escritura a 1,25 veces la tarifa de entrada. Las llamadas cuyo prompt no se
# repite (una página, una pregunta con sus fragmentos) pagarían el recargo sin leer nunca
# la caché; en modo explícito solo se escribe donde el prompt marca un punto de corte.
CACHE_EXPLICITA = {'extra_body': {'prompt_cache_options': {'mode': 'explicit'}}}
PUNTO_DE_CORTE_DE_CACHE = {'prompt_cache_breakpoint': {'mode': 'explicit'}}


def opciones_del_modelo(modelo: str) -> dict[str, Any]:
    # El laboratorio del curso desactiva el razonamiento de gpt-6-luna; se conserva para
    # que las latencias y los costos sean comparables con los de ese laboratorio.
    return {'reasoning': {'effort': 'none'}} if modelo == 'gpt-6-luna' else {}


def imagen_como_entrada(ruta: Path) -> dict[str, str]:
    codificada = base64.b64encode(ruta.read_bytes()).decode()
    return {'type': 'input_image', 'image_url': f'data:image/png;base64,{codificada}'}


def generar(api: OpenAI, instrucciones: str, entrada: Any, *, modelo: str = MODELO_LLM, **extra: Any) -> Respuesta:
    """Una llamada a la API Responses. `entrada` es texto o la lista de mensajes de la API."""
    if es_local(modelo):
        # Ollama no implementa la caché explícita de OpenAI.
        extra.pop('extra_body', None)
    inicio = time.perf_counter()
    crudo = api.responses.create(
        model=modelo, instructions=instrucciones, input=entrada, **opciones_del_modelo(modelo), **extra,
    )
    segundos = time.perf_counter() - inicio
    uso = crudo.usage
    detalles = uso.input_tokens_details
    return Respuesta(
        texto=crudo.output_text,
        tokens_entrada=uso.input_tokens,
        tokens_en_cache=(detalles.cached_tokens or 0) if detalles else 0,
        tokens_escritos_en_cache=getattr(detalles, 'cache_write_tokens', 0) or 0,
        tokens_salida=uso.output_tokens,
        segundos=segundos,
        crudo=crudo,
    )
