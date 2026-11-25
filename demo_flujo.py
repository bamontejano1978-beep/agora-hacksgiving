"""Demo end-to-end de AGORA contra los tres servicios.

Uso:
    python demo_flujo.py
    python demo_flujo.py --texto "quiero toledo-tapas.com por 12 euros"
    python demo_flujo.py --dominio ejemplo.com --precio 12
    python demo_flujo.py --esperar-txt      # DNS real: publica y reintenta
"""

import argparse
import json
import os
import sys

import requests

# En una consola Windows cp1252 los acentos y el euro salen como basura.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

URL_JEFE = os.getenv("URL_JEFE", "http://127.0.0.1:8000").rstrip("/")


def cabecera(n: int, titulo: str) -> None:
    print(f"\n{'=' * 66}\n[{n}] {titulo}\n{'=' * 66}")


def post(ruta: str, payload: dict) -> dict:
    url = f"{URL_JEFE}{ruta}"
    try:
        r = requests.post(url, json=payload, timeout=180)
    except requests.RequestException as e:
        print(f"\nNo puedo hablar con {url}: {type(e).__name__}")
        print("¿Están los tres servicios arrancados? Mira el README.")
        sys.exit(1)
    if r.status_code >= 400:
        print(f"\nPOST {ruta} -> {r.status_code}\n{r.text[:500]}")
        sys.exit(1)
    return r.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo del flujo AGORA")
    parser.add_argument(
        "--texto",
        default="Necesito toledo-tapas.com para el viernes, pago hasta 12 euros",
    )
    parser.add_argument("--dominio", default=None)
    parser.add_argument("--precio", type=float, default=None)
    parser.add_argument(
        "--esperar-txt",
        action="store_true",
        help="si falta el registro TXT, espera a que lo publiques y reintenta",
    )
    args = parser.parse_args()

    entrada: dict = {"texto": args.texto, "pedido": args.texto}
    if args.dominio:
        entrada["dominio"] = args.dominio
    if args.precio:
        entrada["precio_max"] = args.precio

    cabecera(1, "El cliente pide. El Jefe (agente) interpreta el pedido")
    pedido = post("/pedido", entrada)
    print(
        json.dumps(
            {
                "job_id": pedido["job_id"],
                "pedido": pedido["pedido"],
                "dominio": pedido["dominio"],
                "precio_max": pedido["precio_max"],
                "fuente_parseo": pedido["fuente_parseo"],
                "aviso": pedido.get("aviso"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    cabecera(2, "Los trabajadores pujan y el matchmaker ordena")
    for p in pedido["ranking"]:
        print(
            f"  {p['trabajador_id']:22} {p['score']:6.2f} pts"
            f"  precio {p['precio']:5.2f} €  {p['tiempo_min']:3d} min"
            f"  reputación {p['reputacion']:.2f}"
        )
        print(f"    desglose: {p['desglose']}")
    print(f"\n  GANADOR: {pedido['ganador']['trabajador_id']}")
    print(f"  RAZÓN:   {pedido['razon']}")

    cabecera(3, "El Testigo emite el reto; cada trabajador enseña su prueba")
    resultado = post(f"/pedido/{pedido['job_id']}/ejecutar", {})
    reto = resultado["reto"]
    print(f'  Reto: publica en TXT  {reto["registro"]}  el valor  {reto["valor"]}')
    for n, intento in enumerate(resultado.get("intentos") or [], 1):
        print(f"\n  Intento {n}: {intento['trabajador_id']}")
        print(f"    afirma:  {intento.get('entrega')}")
        print(
            f"    TXT verificado: {intento.get('evidencia_ok')}"
            f"  ->  {intento.get('veredicto')} (modo {intento.get('modo')})"
        )
        if not intento.get("evidencia_ok") and intento.get("razon"):
            print(f"    razon:   {intento['razon']}")
        for r in resultado.get("reasignaciones") or []:
            if r["de"] == intento["trabajador_id"]:
                print(f"\n  REASIGNACION: {r['de']} no entrego evidencia -> {r['a']}")

    # Con DNS real el pago queda retenido hasta que el TXT exista. Aquí se puede
    # publicar el registro y reintentar sin salir de la demo.
    if (
        args.esperar_txt
        and resultado["estado"] == "PENDIENTE"
        and resultado["verificacion"]["modo"] == "evidencia"
    ):
        print("\n  Pago RETENIDO: falta el registro TXT.")
        print(f'  Publica en tu DNS:   {reto["registro"]}   TXT   "{reto["valor"]}"')
        print("  (Cloudflare/Namecheap: 30 segundos. El nonce no cambia.)")
        try:
            input("  Pulsa Enter cuando el registro ya se resuelva... ")
        except EOFError:
            pass
        resultado = post(f"/pedido/{pedido['job_id']}/ejecutar", {})
        print(f"  Reintento -> estado: {resultado['estado']}")

    cabecera(4, "Veredicto y liquidación")
    v = resultado["verificacion"]
    print(f"  veredicto:    {v['veredicto']}")
    print(f"  liberar_pago: {v['liberar_pago']}")
    print(f"  modo:         {v['modo']}")
    print(f"  razón:        {v['razon']}")
    if v.get("aviso"):
        print(f"  aviso:        {v['aviso']}")
    if v.get("reputacion_actualizada"):
        print(
            f"  reputación de {resultado['pedido']['ganador']['trabajador_id']}: "
            f"{v['reputacion_actual']}"
        )
    print(f"  estado del pedido: {resultado['estado']}")
    if resultado.get("siguiente"):
        print(f"  siguiente paso:   {resultado['siguiente']}")

    if v["modo"] == "sin_llm":
        print(
            "\n  Sin modelo de juicio configurado no se libera dinero (a propósito).\n"
            "  Exporta OPENROUTER_API_KEY (o usa el connector de OpenRouter en el\n"
            "  Sprite) para ver el veredicto SI y la reputación subir."
        )

    print(f"\nAuditoría completa: {URL_JEFE}/auditoria")
    print("Fin del flujo.")


if __name__ == "__main__":
    main()
