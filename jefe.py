"""Jefe: el agente comprador de AGORA.

Es el agente que vive en un Sprite: entiende el pedido en lenguaje natural (con
el LLM a través del connector, sin credencial dentro de la máquina), convoca
pujas, adjudica con el matchmaker y **ejecuta el pago solo si el Testigo lo
autoriza con evidencia**.

Con AGORA_TRABAJADOR_FANTASMA=1 (arco de demo), si el adjudicatario no publica
el reto TXT el Jefe reasigna al siguiente postor del ranking en la misma
llamada. Sin el interruptor, la falta de evidencia sigue siendo un PENDIENTE
reintentable.
"""

import datetime
import uuid

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from agora import auditoria, config, evidencia, llm, puntuacion
from agora.almacen import Almacen
from agora.modelos import Pedido, PedidoEntrada, Puja

app = FastAPI(title="AGORA Jefe v4", version="4.0.0")
almacen = Almacen(config.PEDIDOS_FILE)

SISTEMA_INTENDENTE = (
    "Eres el Jefe de AGORA. Extraes los datos de un pedido escrito en lenguaje "
    "natural. Responde SOLO con JSON: "
    '{"dominio": "ejemplo.com", "precio_max": 12.0, "pedido": "frase corta"}. '
    "El dominio debe ser un dominio desnudo, sin esquema ni ruta. Si no aparece "
    "un precio, usa 12. Si no aparece un dominio, devuelve cadena vacía."
)


def _post(url: str, payload: dict, timeout: float = 30.0) -> dict:
    try:
        r = requests.post(url, json=payload, timeout=timeout)
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502, detail=f"No puedo hablar con {url}: {type(e).__name__}"
        ) from e
    if r.status_code >= 400:
        codigo = r.status_code if r.status_code < 500 else 502
        raise HTTPException(
            status_code=codigo,
            detail=f"{url} respondio {r.status_code}: {r.text[:300]}",
        )
    try:
        return r.json()
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"{url} no devolvio JSON") from e


def interpretar_pedido(texto: str) -> tuple[dict | None, str | None]:
    """El agente convierte "quiero X por 12 euros" en un pedido estructurado."""
    if not llm.activo():
        return None, f"LLM no activo ({llm.motivo()})"
    try:
        respuesta = llm.chat(
            f"Pedido del cliente:\n<<<TEXTO\n{texto}\nTEXTO>>>",
            sistema=SISTEMA_INTENDENTE,
            max_tokens=200,
        )
    except llm.ErrorLLM as e:
        return None, str(e)
    datos = llm.extraer_json(respuesta)
    return (datos, None) if datos else (None, "respuesta no interpretable")


def _resolver_entrada(
    entrada: PedidoEntrada,
) -> tuple[str, float, str, str, str | None]:
    """Normaliza el pedido: (dominio, precio_max, descripcion, fuente, aviso)."""
    texto = (entrada.texto or "").strip()
    dominio = evidencia.normalizar(entrada.dominio or "")
    precio_max = entrada.precio_max
    descripcion = (entrada.pedido or texto or "").strip()
    fuente, aviso = "explicito", None

    if texto and (not dominio or precio_max is None):
        interpretado, error = interpretar_pedido(texto)
        if interpretado is None:
            aviso = (
                f"El agente no pudo interpretar el texto ({error}). "
                "Envia dominio y precio_max explicitos."
            )
        else:
            if not dominio:
                dominio = evidencia.normalizar(str(interpretado.get("dominio") or ""))
            if precio_max is None:
                try:
                    precio_max = float(interpretado.get("precio_max"))
                except (TypeError, ValueError):
                    precio_max = None
                if precio_max is not None and precio_max <= 0:
                    precio_max = None
            descripcion = descripcion or str(interpretado.get("pedido") or "")
            fuente = "llm"

    return (
        dominio,
        float(precio_max or config.PRECIO_MAX_DEFECTO),
        descripcion,
        fuente,
        aviso,
    )


def _estado_y_siguiente(
    verificacion: dict, job_id: str, reto: dict
) -> tuple[str, str]:
    """Estado del pedido y qué hacer a continuación, en un solo sitio."""
    if verificacion.get("liberar_pago"):
        return "PAGADO", "Pago liberado y reputacion actualizada."
    if verificacion.get("modo") == "llm" and verificacion.get("veredicto") == "NO":
        return "RECHAZADO", "Se devuelve el importe al cliente. No se reintenta."
    if verificacion.get("modo") == "evidencia":
        return "PENDIENTE", (
            f"Publica el registro TXT y repite POST /pedido/{job_id}/ejecutar: "
            f'{reto.get("registro")} TXT "{reto.get("valor")}"'
        )
    if verificacion.get("modo") == "sin_llm":
        return "PENDIENTE", (
            f"Configura el LLM y repite POST /pedido/{job_id}/ejecutar."
        )
    return "PENDIENTE", f"Repite POST /pedido/{job_id}/ejecutar."


def _leer_pedido(job_id: str) -> dict:
    pedido = almacen.cargar().get("pedidos", {}).get(job_id)
    if not pedido:
        raise HTTPException(status_code=404, detail=f"No existe el pedido {job_id}")
    return pedido


def _guardar_pedido(job_id: str, datos: dict) -> None:
    def _guardar(almacenado: dict) -> dict:
        almacenado.setdefault("pedidos", {})[job_id] = datos
        return almacenado

    almacen.actualizar(_guardar)


def _intentar(job_id: str, pedido: dict, trabajador_id: str) -> tuple[dict, dict, dict]:
    """Un intento completo: reto -> entrega -> verificación. No decide nada."""
    dominio = pedido["dominio"]
    reto = _post(
        f"{config.URL_TESTIGO}/reto",
        {"job_id": job_id, "dominio": dominio},
        timeout=15,
    )
    entrega = _post(
        f"{config.URL_TRABAJADOR}/comprar",
        {
            "job_id": job_id,
            "dominio": dominio,
            "trabajador_id": trabajador_id,
            "nonce": reto.get("nonce"),
        },
        timeout=20,
    )
    verificacion = _post(
        f"{config.URL_TESTIGO}/verificar",
        {
            "job_id": job_id,
            "dominio": dominio,
            "trabajador_id": trabajador_id,
            "pedido": pedido["pedido"],
            "entrega": entrega.get("entrega", ""),
            "nonce": reto.get("nonce"),
        },
        timeout=120,
    )
    return reto, entrega, verificacion


def _siguiente_postor(pedido: dict, intentados: set[str]) -> dict | None:
    """Siguiente del ranking original que todavía no lo haya intentado."""
    for puja in pedido.get("ranking") or []:
        if puja.get("trabajador_id") not in intentados:
            return puja
    return None


def _fallo_de_entrega(estado: str, verificacion: dict) -> bool:
    """El postor no demostró nada: el Testigo no encontró el TXT del reto."""
    return estado == "PENDIENTE" and verificacion.get("modo") == "evidencia"


@app.get("/")
def home():
    return {
        "agora": "Jefe v4",
        "rol": "Agente comprador: interpreta, negocia, adjudica y paga con evidencia",
        "llm_activo": llm.activo(),
        "modo_llm": llm.motivo(),
        "trabajador": config.URL_TRABAJADOR,
        "testigo": config.URL_TESTIGO,
        "modo_demo": config.DEMO,
        "fantasma": config.TRABAJADOR_FANTASMA,
        "auditoria": "/auditoria",
    }


@app.get("/salud")
def salud():
    return {
        "servicio": "jefe",
        "ok": True,
        "llm_activo": llm.activo(),
        "demo": config.DEMO,
    }


@app.post("/pedido", response_model=Pedido)
def crear_pedido(entrada: PedidoEntrada):
    """Crea el job, convoca pujas y adjudica. No compra nada todavía."""
    dominio, precio_max, descripcion, fuente, aviso = _resolver_entrada(entrada)
    if not dominio:
        crudo = (entrada.dominio or "").strip()
        raise HTTPException(
            status_code=422,
            detail=(
                f"Dominio no valido: {crudo}"
                if crudo
                else "Falta el dominio: pasa 'dominio' o un texto que el agente pueda interpretar."
            ),
        )
    if not evidencia.dominio_valido(dominio):
        raise HTTPException(status_code=422, detail=f"Dominio no valido: {dominio}")

    job_id = "job-" + uuid.uuid4().hex[:8]
    respuesta = _post(
        f"{config.URL_TRABAJADOR}/pujar",
        {"job_id": job_id, "dominio": dominio},
        timeout=15,
    )
    try:
        pujas = [Puja(**p) for p in respuesta.get("pujas", [])]
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=502, detail=f"Pujas invalidas: {e}") from e
    if not pujas:
        raise HTTPException(status_code=502, detail="El trabajador no devolvio pujas")

    ranking, descartadas = puntuacion.puntuar(pujas, precio_max)
    if not ranking:
        raise HTTPException(
            status_code=409,
            detail=f"Ninguna puja cabe en {precio_max:.2f} EUR. Sube precio_max.",
        )
    ganador = ranking[0]
    pedido = Pedido(
        job_id=job_id,
        pedido=descripcion or f"Comprar {dominio}",
        dominio=dominio,
        precio_max=precio_max,
        estado="ADJUDICADO",
        creado=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        fuente_parseo=fuente,
        ranking=ranking,
        ganador=ganador,
        razon=puntuacion.razon(ganador, descartadas, precio_max),
        aviso=aviso,
    )
    _guardar_pedido(job_id, pedido.model_dump(mode="json"))
    return pedido


@app.post("/pedido/{job_id}/ejecutar")
def ejecutar(job_id: str):
    """Reto -> entrega -> verificación -> pago, o reasignación al siguiente.

    Con AGORA_TRABAJADOR_FANTASMA=1, si el adjudicatario no demuestra nada el
    Jefe pasa al siguiente postor del ranking en esta misma llamada. El pedido
    solo queda RECHAZADO cuando se agotan los candidatos sin evidencia.
    """
    pedido = _leer_pedido(job_id)
    if pedido["estado"] in ("PAGADO", "RECHAZADO"):
        raise HTTPException(
            status_code=409, detail=f"El pedido ya esta {pedido['estado']}"
        )

    intentos = [dict(i) for i in pedido.get("intentos") or []]
    reasignaciones = [dict(r) for r in pedido.get("reasignaciones") or []]
    intentados = {i.get("trabajador_id") for i in intentos if i.get("trabajador_id")}

    while True:
        trabajador_id = (pedido.get("ganador") or {}).get("trabajador_id")
        if not trabajador_id:
            raise HTTPException(
                status_code=409, detail="El pedido no tiene adjudicatario"
            )

        reto, entrega, verificacion = _intentar(job_id, pedido, trabajador_id)
        estado, siguiente = _estado_y_siguiente(verificacion, job_id, reto)

        intentados.add(trabajador_id)
        intentos.append(
            {
                "trabajador_id": trabajador_id,
                "resultado": estado,
                "veredicto": verificacion.get("veredicto"),
                "modo": verificacion.get("modo"),
                "liberar_pago": bool(verificacion.get("liberar_pago")),
                "evidencia_ok": bool(
                    (verificacion.get("evidencia") or {}).get("reto", {}).get("ok")
                ),
                "razon": str(verificacion.get("razon") or "")[:300],
                "entrega": str(entrega.get("entrega") or "")[:400],
                # Evidencia completa del veredicto y reto emitido: la página de
                # auditoría puede reproducir el dig sin consultar al Testigo.
                "reto": reto,
                "verificacion": verificacion,
            }
        )

        if not (
            config.TRABAJADOR_FANTASMA and _fallo_de_entrega(estado, verificacion)
        ):
            break

        relevo = _siguiente_postor(pedido, intentados)
        if not relevo:
            estado = "RECHAZADO"
            siguiente = (
                "Ningun postor restante publico la evidencia: se devuelve el "
                "importe al cliente."
            )
            break
        reasignaciones.append(
            {
                "de": trabajador_id,
                "a": relevo["trabajador_id"],
                "motivo": "sin evidencia: el reto TXT no se publico",
            }
        )
        pedido = dict(
            pedido,
            ganador=relevo,
            razon=(
                f"Reasignado a {relevo['trabajador_id']}: {trabajador_id} no "
                "publico el reto TXT y el pago sigue retenido."
            ),
        )

    actualizado = dict(pedido)
    actualizado.update(
        estado=estado,
        reto=reto,
        entrega=entrega,
        veredicto=verificacion,
        intentos=intentos,
        reasignaciones=reasignaciones,
    )
    _guardar_pedido(job_id, actualizado)
    return {
        "job_id": job_id,
        "estado": estado,
        "siguiente": siguiente,
        "reto": reto,
        "entrega": entrega,
        "verificacion": verificacion,
        "intentos": intentos,
        "reasignaciones": reasignaciones,
        "pedido": actualizado,
    }


@app.get("/pedido/{job_id}")
def consultar_pedido(job_id: str):
    return _leer_pedido(job_id)


@app.get("/pedidos")
def listar_pedidos():
    pedidos = almacen.cargar().get("pedidos", {})
    return {
        "total": len(pedidos),
        "pedidos": [
            {
                "job_id": p.get("job_id"),
                "dominio": p.get("dominio"),
                "estado": p.get("estado"),
                "ganador": (p.get("ganador") or {}).get("trabajador_id"),
            }
            for p in pedidos.values()
        ],
    }


def _registro_testigo() -> tuple[dict | None, str | None]:
    """Libro del Testigo para la página. Si no responde, la página sigue."""
    try:
        r = requests.get(f"{config.URL_TESTIGO}/jobs", timeout=3)
    except requests.RequestException as e:
        return None, f"No puedo leer el registro del Testigo: {type(e).__name__}"
    if not r.ok:
        return None, f"El Testigo respondio {r.status_code}"
    try:
        datos = r.json()
    except ValueError:
        return None, "El Testigo no devolvio JSON"
    if not isinstance(datos, dict):
        return None, "El registro del Testigo no tiene la forma esperada"
    return datos, None


@app.get("/auditoria", response_class=HTMLResponse)
def auditoria_html():
    """Libro de pedidos + veredictos + reputación, en una página sin build."""
    testigo_datos, error = _registro_testigo()
    return HTMLResponse(
        auditoria.pagina(almacen.cargar().get("pedidos", {}), testigo_datos, error)
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.HOST, port=config.puerto(8000))
