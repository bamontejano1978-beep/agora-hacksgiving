"""Configuración de AGORA, siempre por entorno (12-factor)."""

import os


def _bool(nombre: str, defecto: bool = False) -> bool:
    valor = os.getenv(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in ("1", "true", "yes", "si", "sí", "on")


def _float(nombre: str, defecto: float) -> float:
    try:
        return float(os.getenv(nombre) or defecto)
    except (TypeError, ValueError):
        return defecto


def _int(nombre: str, defecto: int) -> int:
    try:
        return int(os.getenv(nombre) or defecto)
    except (TypeError, ValueError):
        return defecto


def puerto(defecto: int) -> int:
    """Puerto HTTP del servicio. En Fly.io llega en PORT."""
    return _int("PORT", defecto)


HOST = os.getenv("HOST", "127.0.0.1")

# Dónde viven los otros dos servicios (en Fly: *.internal)
URL_TRABAJADOR = os.getenv("URL_TRABAJADOR", "http://127.0.0.1:8001").rstrip("/")
URL_TESTIGO = os.getenv("URL_TESTIGO", "http://127.0.0.1:8002").rstrip("/")

# LLM. Con el connector de Sprites, OPENROUTER_BASE_URL apunta al gateway y la
# credencial no vive en la máquina.
URL_LLM = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
CLAVE_LLM = os.getenv("OPENROUTER_API_KEY", "")
MODELO = os.getenv("AGORA_MODELO", "openrouter/free")
LLM_DESHABILITADO = os.getenv("AGORA_LLM", "").strip().lower() in (
    "off",
    "0",
    "false",
    "no",
)

# 1 = zona DNS de demo local (para probar el flujo sin un dominio real).
DEMO = _bool("AGORA_DEMO", False)

# Persistencia. En Fly con volumen: JOBS_FILE=/data/jobs.json
JOBS_FILE = os.getenv("JOBS_FILE", os.path.join("datos", "jobs.json"))
PEDIDOS_FILE = os.getenv("PEDIDOS_FILE", os.path.join("datos", "pedidos.json"))
DEMO_DNS_FILE = os.getenv("DEMO_DNS_FILE", os.path.join("datos", "demo_dns.json"))

# Resolver DNS alternativo ("host" o "host:puerto"). Vacio = el del sistema.
DNS_SERVIDOR = os.getenv("AGORA_DNS_SERVIDOR", "").strip()

# Pesos del matchmaker: reputación, precio y tiempo compiten entre sí.
PESO_REPUTACION = _float("PESO_REPUTACION", 0.55)
PESO_PRECIO = _float("PESO_PRECIO", 0.30)
PESO_TIEMPO = _float("PESO_TIEMPO", 0.15)
TIEMPO_REFERENCIA_MIN = _int("TIEMPO_REFERENCIA_MIN", 120)

PRECIO_MAX_DEFECTO = _float("PRECIO_MAX_DEFECTO", 12.0)
MINUTOS_VALIDEZ_RETO = _int("MINUTOS_VALIDEZ_RETO", 10)
