"""Del texto del juez al pago. Aquí se decide si se mueve dinero.

Dos reglas duras:

1. **Sin evidencia no hay pago.** Si el reto DNS TXT no está publicado, el
   veredicto es NO aunque el modelo diga SI. El LLM no puede abrir la caja.
2. **Sin LLM no hay pago.** Si no hay modelo configurado, el veredicto es
   INDETERMINADO y `liberar_pago` es False. El modo degradado nunca paga.

El parser no usa `startswith("SI")`, que aprobaba "SIN EMBARGO, el dominio no
está registrado" y rechazaba "SÍ, cumple".
"""

import re

from .llm import extraer_json

RE_SI = re.compile(r"^s[ií]\b")
RE_NO = re.compile(r"^no\b")
MARCA_INICIAL = re.compile(r"^[`*#>\-\s\"'«»“”]+")
SI_SUELTO = re.compile(r"\bs[ií]\b")
NO_SUELTO = re.compile(r"\bno\b")

RESPUESTAS_SI = ("si", "sí", "yes", "true", "aprobado")
RESPUESTAS_NO = ("no", "false", "rechazado")


def _limpiar(texto: str) -> str:
    return MARCA_INICIAL.sub("", texto.strip())


def parsear_veredicto(texto: str | None) -> str | None:
    """Devuelve "SI", "NO" o None (no concluyente)."""
    if not texto:
        return None
    limpio = _limpiar(str(texto))

    # 1) JSON explícito, que es lo que pide el prompt.
    datos = extraer_json(limpio)
    if isinstance(datos, dict):
        valor = str(datos.get("veredicto", "")).strip().lower()
        if valor in RESPUESTAS_SI:
            return "SI"
        if valor in RESPUESTAS_NO:
            return "NO"

    # 2) Primera palabra de la primera línea.
    primera = _limpiar(limpio.splitlines()[0] if limpio else "").lower()
    if RE_SI.match(primera):
        return "SI"
    if RE_NO.match(primera):
        return "NO"

    # 3) Frase corta con un único candidato ("el trabajo cumple: SI").
    if len(limpio) <= 60:
        hay_si = bool(SI_SUELTO.search(limpio.lower()))
        hay_no = bool(NO_SUELTO.search(limpio.lower()))
        if hay_si != hay_no:
            return "SI" if hay_si else "NO"

    return None


def decidir(evidencia_ok: bool, texto_llm: str | None, llm_activo: bool) -> dict:
    """Regla de negocio: quién puede liberar el pago y con qué motivo."""
    if not evidencia_ok:
        return {
            "veredicto": "NO",
            "liberar_pago": False,
            "modo": "evidencia",
            "razon": (
                "La evidencia no demuestra control del dominio: falta el registro "
                "TXT del reto. No se libera el pago."
            ),
        }
    if not llm_activo:
        return {
            "veredicto": "INDETERMINADO",
            "liberar_pago": False,
            "modo": "sin_llm",
            "razon": (
                "Evidencia correcta, pero no hay modelo de juicio configurado. "
                "Por seguridad no se libera el pago sin veredicto."
            ),
        }
    veredicto = parsear_veredicto(texto_llm)
    if veredicto is None:
        return {
            "veredicto": "INDETERMINADO",
            "liberar_pago": False,
            "modo": "llm",
            "razon": "El juez no devolvió un veredicto claro (ni SI ni NO).",
        }
    return {
        "veredicto": veredicto,
        "liberar_pago": veredicto == "SI",
        "modo": "llm",
        "razon": (texto_llm or "").strip()[:300],
    }
