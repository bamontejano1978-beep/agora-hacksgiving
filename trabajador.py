"""Trabajadores: compiten por el trabajo y pujan con su reputación real.

La reputación no se declara aquí: es propiedad del Testigo. Todos empiezan en 4.5
y la diferencia la marca el historial verificado.
"""

import requests
from fastapi import FastAPI, HTTPException

from agora import config, evidencia
from agora.modelos import CompraRequest, CompraRespuesta, Puja, PujarRequest, PujasRespuesta

app = FastAPI(title="AGORA Trabajador v4", version="4.0.0")

REPUTACION_INICIAL = 4.5

TRABAJADORES: dict[str, dict] = {
    "trabajador-dominios": {"especialidad": "dominios", "precio": 10.0, "tiempo_min": 60},
    "trabajador-rapido": {"especialidad": "dominios", "precio": 12.0, "tiempo_min": 10},
    "trabajador-barato": {"especialidad": "dominios", "precio": 9.0, "tiempo_min": 120},
}


def _reputaciones() -> dict:
    """Reputación viva del Testigo. Si no responde, se usa la de partida."""
    try:
        r = requests.get(f"{config.URL_TESTIGO}/reputacion", timeout=2.5)
        datos = r.json() if r.ok else None
    except (requests.RequestException, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _reputacion(trabajador_id: str, reputaciones: dict) -> float:
    ficha = reputaciones.get(trabajador_id)
    valor = ficha.get("reputacion") if isinstance(ficha, dict) else None
    try:
        return max(1.0, min(5.0, float(valor)))
    except (TypeError, ValueError):
        return REPUTACION_INICIAL


@app.get("/")
def home():
    return {
        "agora": "Trabajador v4",
        "rol": "Compite por trabajos con su reputacion real",
        "trabajadores": list(TRABAJADORES),
        "testigo": config.URL_TESTIGO,
    }


@app.get("/salud")
def salud():
    return {
        "servicio": "trabajador",
        "ok": True,
        "testigo": config.URL_TESTIGO,
        "demo": config.DEMO,
    }


@app.post("/pujar", response_model=PujasRespuesta)
def pujar(peticion: PujarRequest):
    if not evidencia.dominio_valido(peticion.dominio):
        raise HTTPException(status_code=422, detail="Dominio no valido")
    reputaciones = _reputaciones()
    pujas = [
        Puja(
            trabajador_id=trabajador_id,
            especialidad=info["especialidad"],
            precio=float(info["precio"]),
            tiempo_min=int(info["tiempo_min"]),
            reputacion=_reputacion(trabajador_id, reputaciones),
        )
        for trabajador_id, info in TRABAJADORES.items()
    ]
    return PujasRespuesta(job_id=peticion.job_id, pujas=pujas)


@app.post("/comprar", response_model=CompraRespuesta)
def comprar(peticion: CompraRequest):
    dominio = evidencia.normalizar(peticion.dominio)
    if not evidencia.dominio_valido(dominio):
        raise HTTPException(status_code=422, detail="Dominio no valido")
    if peticion.trabajador_id not in TRABAJADORES:
        raise HTTPException(status_code=404, detail="Trabajador desconocido")

    publicado = False
    if config.DEMO and peticion.nonce:
        # En demo, el "registrador" es la zona local del Testigo: el trabajador
        # publica el reto exactamente como lo haría en DNS real.
        try:
            r = requests.post(
                f"{config.URL_TESTIGO}/demo/txt",
                json={"dominio": dominio, "nonce": peticion.nonce},
                timeout=5,
            )
            publicado = bool(r.ok and r.json().get("publicado"))
        except (requests.RequestException, ValueError):
            publicado = False

    donde = (
        "y publico el reto TXT en la zona de demo"
        if publicado
        else "sin publicar el reto TXT"
    )
    return CompraRespuesta(
        job_id=peticion.job_id,
        trabajador_id=peticion.trabajador_id,
        dominio=dominio,
        entrega=(
            f"Compra simulada de {dominio} por {peticion.trabajador_id} {donde}. "
            "El Testigo debe verificar el reto antes de liberar el pago."
        ),
        simulado=True,
        publicado_en_zona_demo=publicado,
        aviso=(
            "AGORA no compra dominios: la entrega es una simulacion explicita. "
            "La prueba de control es el registro TXT del reto."
        ),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.HOST, port=config.puerto(8001))
