"""LLM de prueba con la misma forma que OpenRouter.

Sirve para verificar el flujo end-to-end (intérprete del pedido + juez) sin
gastar créditos ni depender de la red. Se levanta en el puerto 18003 y se apunta
el Jefe y el Testigo con:

    OPENROUTER_BASE_URL=http://127.0.0.1:18003/v1
"""

import os

from fastapi import FastAPI, Request

app = FastAPI(title="Stub LLM AGORA")

RESPUESTA_PEDIDO = (
    '{"dominio": "toledo-tapas.com", "precio_max": 12.0, '
    '"pedido": "Comprar toledo-tapas.com para el viernes"}'
)


@app.get("/salud")
def salud():
    return {"servicio": "stub_llm", "ok": True}


@app.post("/v1/chat/completions")
async def completions(peticion: Request):
    cuerpo = await peticion.json()
    texto = str(cuerpo.get("messages", [{}])[-1].get("content", ""))

    if "publicado=" in texto:
        if "publicado=True" in texto:
            contenido = (
                '{"veredicto": "SI", "razon": "El reto TXT esta publicado: '
                'el trabajador controla el dominio."}'
            )
        else:
            contenido = (
                '{"veredicto": "NO", "razon": "Sin el reto TXT no hay prueba '
                'de control del dominio."}'
            )
    else:
        contenido = RESPUESTA_PEDIDO

    return {
        "id": "stub-1",
        "object": "chat.completion",
        "model": "stub",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": contenido},
                "finish_reason": "stop",
            }
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "18003")))
