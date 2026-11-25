"""Evidencia verificable de que alguien controla un dominio.

La prueba es un reto DNS TXT: el Testigo genera un nonce y el trabajador debe
publicar `agora-verify=<nonce>` en `_agora.<dominio>`. Sin control de la zona no
se puede publicar, así que no se puede falsificar.

No se hace ninguna petición HTTP al dominio: el único tráfico saliente es la
consulta TXT, que no abre conexión al destino. Al no haber cliente HTTP no hay
superficie de SSRF. `dominio_valido` rechaza IPs y TLDs internos (`.internal`,
`.local`...) para que la consulta tampoco se pueda dirigir a zonas privadas.
"""

import functools
import re

from . import config
from .almacen import Almacen

# Un dominio real: etiquetas alfanuméricas y un TLD alfabético. Rechaza IPs,
# esquemas, rutas, puertos y cualquier carácter que no sea de etiqueta DNS.
RE_DOMINIO = re.compile(
    r"^(?=.{4,253}$)(?!-)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)

# TLDs que no son dominios registrables y que resuelven a redes internas.
SUFIJOS_NO_PUBLICOS = (
    "internal",
    "local",
    "localhost",
    "localdomain",
    "lan",
    "home",
    "onion",
)


def normalizar(dominio: str) -> str:
    """Minúsculas y sin punto final. No acepta URLs."""
    d = (dominio or "").strip().lower()
    if d.startswith("http://") or d.startswith("https://"):
        return ""
    return d.rstrip(".")


def dominio_valido(dominio: str) -> bool:
    d = normalizar(dominio)
    if not d or not RE_DOMINIO.match(d):
        return False
    return d.rsplit(".", 1)[-1] not in SUFIJOS_NO_PUBLICOS


def registro_reto(dominio: str) -> str:
    return f"_agora.{dominio}"


def valor_reto(nonce: str) -> str:
    return f"agora-verify={nonce}"


@functools.lru_cache(maxsize=1)
def _resolver():
    """Resolver DNS: el del sistema o el que diga AGORA_DNS_SERVIDOR."""
    import dns.resolver  # dnspython

    if not config.DNS_SERVIDOR:
        return dns.resolver.Resolver()
    host, _, puerto = config.DNS_SERVIDOR.partition(":")
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = [host]
    if puerto:
        resolver.port = int(puerto)
    resolver.timeout = 3
    resolver.lifetime = 5
    return resolver


def txt_dns(dominio: str, nonce: str) -> dict:
    """Consulta TXT de verdad, contra el resolver configurado."""
    nombre = registro_reto(dominio)
    esperado = valor_reto(nonce)
    base = {
        "fuente": "dns",
        "servidor": config.DNS_SERVIDOR or "sistema",
        "nombre": nombre,
        "esperado": esperado,
        "valores": [],
    }
    try:
        resolver = _resolver()
    except ImportError:
        return {**base, "ok": False, "detalle": "dnspython no instalado"}
    try:
        respuestas = resolver.resolve(nombre, "TXT")
        valores = [b"".join(r.strings).decode("utf-8", "replace") for r in respuestas]
    except Exception as e:  # NXDOMAIN, NoAnswer, timeout...
        return {**base, "ok": False, "detalle": type(e).__name__}
    return {**base, "ok": esperado in valores, "valores": valores}


def txt_demo(dominio: str, nonce: str) -> dict:
    """Zona DNS de demo local (AGORA_DEMO=1), con la misma forma que txt_dns."""
    zona = Almacen(config.DEMO_DNS_FILE).cargar()
    valores = zona.get(dominio, [])
    esperado = valor_reto(nonce)
    return {
        "ok": esperado in valores,
        "fuente": "demo",
        "nombre": registro_reto(dominio),
        "esperado": esperado,
        "valores": valores,
        "detalle": "zona DNS de demo local, no DNS real",
    }


def publicar_txt_demo(dominio: str, nonce: str) -> dict:
    """Publica el reto en la zona de demo, como haría el dueño en su DNS."""
    valor = valor_reto(nonce)

    def _publicar(zona: dict) -> dict:
        valores = zona.setdefault(dominio, [])
        if valor not in valores:
            valores.append(valor)
        return zona

    Almacen(config.DEMO_DNS_FILE).actualizar(_publicar)
    return {
        "publicado": True,
        "fuente": "demo",
        "nombre": registro_reto(dominio),
        "valor": valor,
    }


def reunir(dominio: str, nonce: str | None) -> dict:
    """La evidencia completa. Sin reto no se consulta nada: no hay nada que probar."""
    d = normalizar(dominio)
    if not dominio_valido(d):
        return {
            "dominio": dominio,
            "dominio_valido": False,
            "ok": False,
            "reto": {"ok": False, "detalle": "dominio no valido"},
        }
    if not nonce:
        return {
            "dominio": d,
            "dominio_valido": True,
            "ok": False,
            "reto": {"ok": False, "detalle": "sin nonce: no hay reto que verificar"},
        }
    reto = txt_demo(d, nonce) if config.DEMO else txt_dns(d, nonce)
    return {
        "dominio": d,
        "dominio_valido": True,
        "ok": bool(reto["ok"]),
        "reto": reto,
    }
