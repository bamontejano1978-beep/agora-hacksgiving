"""Cliente LLM único (OpenRouter o el gateway de un connector de Sprites).

En un Sprite con el connector de OpenRouter, `OPENROUTER_BASE_URL` apunta al
gateway y la credencial se queda fuera de la máquina: por eso aquí no se exige
`OPENROUTER_API_KEY` para considerar el LLM activo.
"""

import json
import re

import requests

from . import config

URL_PUBLICA = "https://openrouter.ai/api/v1"


class ErrorLLM(RuntimeError):
    pass


def activo() -> bool:
    """¿Hay un modelo utilizable? Con gateway no hace falta clave local."""
    if config.LLM_DESHABILITADO:
        return False
    return bool(config.CLAVE_LLM) or config.URL_LLM != URL_PUBLICA


def motivo() -> str:
    """Por qué está (o no) activo, para los mensajes de la API."""
    if config.LLM_DESHABILITADO:
        return "AGORA_LLM=off"
    if not activo():
        return "sin clave y sin gateway"
    return "clave" if config.CLAVE_LLM else "gateway"


def chat(prompt: str, sistema: str | None = None, max_tokens: int = 400) -> str:
    mensajes = []
    if sistema:
        mensajes.append({"role": "system", "content": sistema})
    mensajes.append({"role": "user", "content": prompt})
    cabeceras = {
        "Content-Type": "application/json",
        "HTTP-Referer": "https://fly.io",
        "X-Title": "AGORA Hacksgiving",
    }
    if config.CLAVE_LLM:
        cabeceras["Authorization"] = f"Bearer {config.CLAVE_LLM}"
    try:
        r = requests.post(
            f"{config.URL_LLM}/chat/completions",
            headers=cabeceras,
            json={
                "model": config.MODELO,
                "messages": mensajes,
                "max_tokens": max_tokens,
                "temperature": 0,
            },
            timeout=45,
        )
    except requests.RequestException as e:
        raise ErrorLLM(f"red: {type(e).__name__}") from e
    if r.status_code >= 400:
        raise ErrorLLM(f"HTTP {r.status_code}: {r.text[:200]}")
    try:
        datos = r.json()
    except ValueError as e:
        raise ErrorLLM("respuesta no JSON") from e
    if "error" in datos:
        raise ErrorLLM(str(datos["error"])[:200])
    try:
        contenido = datos["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ErrorLLM("respuesta sin choices") from e
    if isinstance(contenido, list):  # algunos modelos devuelven partes
        contenido = "".join(
            parte.get("text", "") for parte in contenido if isinstance(parte, dict)
        )
    if not contenido or not str(contenido).strip():
        raise ErrorLLM("respuesta vacía")
    return str(contenido)


def extraer_json(texto: str) -> dict | None:
    """Saca el primer objeto JSON de una respuesta con markdown alrededor."""
    if not texto:
        return None
    limpio = re.sub(r"^```[a-zA-Z]*\s*", "", texto.strip())
    limpio = re.sub(r"\s*```$", "", limpio)
    inicio, fin = limpio.find("{"), limpio.rfind("}")
    if inicio == -1 or fin <= inicio:
        return None
    try:
        datos = json.loads(limpio[inicio : fin + 1])
    except json.JSONDecodeError:
        return None
    return datos if isinstance(datos, dict) else None
