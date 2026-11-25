"""End-to-end del reto DNS TXT contra DNS real (AGORA_DEMO=0).

Comprueba que la verificación funciona igual sin la zona de demo:

  1. primer /ejecutar  -> PENDIENTE, evidencia por DNS, sin TXT (NXDOMAIN)
  2. se publica el TXT con el nonce emitido
  3. segundo /ejecutar -> mismo nonce, evidencia ok, SI, PAGADO, reputación sube

El servidor autoritativo es local porque escribir en DNS público exige ser dueño
del dominio, pero habla DNS de verdad: consulta y respuesta UDP con dnspython.
Lo único que queda fuera de la prueba es el registrador.

Además se consulta DNS público real (el resolver del sistema) para demostrar que
un dominio sin registro devuelve NXDOMAIN/NoAnswer y no un falso positivo.

Uso:  python tests/e2e_dns_real.py
"""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import dns.flags
import dns.message
import dns.rcode
import dns.rdatatype
import dns.rrset
import requests

try:  # consola Windows cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

PY = sys.executable
DOMINIO = "agora.test"
PUERTO_DNS = 15353
P_JEFE, P_TRABAJADOR, P_TESTIGO, P_LLM = 18100, 18101, 18102, 18103


class DNSAutoritativo:
    """Servidor DNS mínimo: responde TXT de su zona y NXDOMAIN del resto."""

    def __init__(self, puerto: int = PUERTO_DNS):
        self.zonas: dict[str, str] = {}
        self.puerto = puerto
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", puerto))
        self._parar = False
        self._hilo = threading.Thread(target=self._bucle, daemon=True)

    def arrancar(self) -> "DNSAutoritativo":
        self._hilo.start()
        return self

    def publicar(self, nombre: str, valor: str) -> None:
        self.zonas[nombre.lower().rstrip(".")] = valor

    def parar(self) -> None:
        self._parar = True
        self._sock.close()

    def _bucle(self) -> None:
        while not self._parar:
            try:
                datos, origen = self._sock.recvfrom(4096)
            except OSError:
                return
            try:
                respuesta = self._responder(datos)
            except Exception:  # consulta malformada: se ignora
                continue
            try:
                self._sock.sendto(respuesta, origen)
            except OSError:
                return

    def _responder(self, datos: bytes) -> bytes:
        consulta = dns.message.from_wire(datos)
        respuesta = dns.message.make_response(consulta)
        respuesta.flags |= dns.flags.AA
        if consulta.question:
            pregunta = consulta.question[0]
            nombre = pregunta.name.to_text().lower().rstrip(".")
            if pregunta.rdtype == dns.rdatatype.TXT and nombre in self.zonas:
                respuesta.answer.append(
                    dns.rrset.from_text(
                        f"{nombre}.",
                        60,
                        "IN",
                        "TXT",
                        f'"{self.zonas[nombre]}"',
                    )
                )
            else:
                respuesta.set_rcode(dns.rcode.NXDOMAIN)
        return respuesta.to_wire()


def esperar(url: str, intentos: int = 40) -> None:
    for _ in range(intentos):
        try:
            if requests.get(url, timeout=1).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise SystemExit(f"No arrancó {url}")


def lanzar(script: str, puerto: int, entorno: dict) -> subprocess.Popen:
    env = {**entorno, "PORT": str(puerto)}
    return subprocess.Popen(
        [PY, script],
        cwd=str(RAIZ),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def main() -> int:
    fallos: list[str] = []

    def comprobar(condicion: bool, descripcion: str) -> None:
        print(f"  {'OK  ' if condicion else 'FALLA'} {descripcion}")
        if not condicion:
            fallos.append(descripcion)

    tmp = Path(tempfile.mkdtemp(prefix="agora-e2e-dns-"))
    dns = DNSAutoritativo().arrancar()
    procesos: list[subprocess.Popen] = []
    entorno = {
        **os.environ,
        "AGORA_DEMO": "0",  # DNS real, no zona de demo
        "AGORA_DNS_SERVIDOR": f"127.0.0.1:{PUERTO_DNS}",
        "OPENROUTER_BASE_URL": f"http://127.0.0.1:{P_LLM}/v1",
        "JOBS_FILE": str(tmp / "jobs.json"),
        "PEDIDOS_FILE": str(tmp / "pedidos.json"),
        "URL_TRABAJADOR": f"http://127.0.0.1:{P_TRABAJADOR}",
        "URL_TESTIGO": f"http://127.0.0.1:{P_TESTIGO}",
    }

    try:
        print("Arrancando servicios (DNS real, AGORA_DEMO=0)...")
        procesos.append(lanzar("tests/stub_llm.py", P_LLM, entorno))
        procesos.append(lanzar("testigo.py", P_TESTIGO, entorno))
        procesos.append(lanzar("trabajador.py", P_TRABAJADOR, entorno))
        procesos.append(lanzar("jefe.py", P_JEFE, entorno))
        for puerto in (P_LLM, P_TESTIGO, P_TRABAJADOR, P_JEFE):
            esperar(f"http://127.0.0.1:{puerto}/salud")
        print("  servicios listos\n")

        print("1) Pedido y primera ejecución (aún sin TXT)")
        pedido = requests.post(
            f"http://127.0.0.1:{P_JEFE}/pedido",
            json={"dominio": DOMINIO, "precio_max": 12},
            timeout=30,
        ).json()
        job_id = pedido["job_id"]
        primero = requests.post(
            f"http://127.0.0.1:{P_JEFE}/pedido/{job_id}/ejecutar", timeout=120
        ).json()
        ev1 = primero["verificacion"]["evidencia"]
        nonce = primero["reto"]["nonce"]
        comprobar(primero["estado"] == "PENDIENTE", "estado PENDIENTE (reintentable)")
        comprobar(
            primero["verificacion"]["modo"] == "evidencia",
            "veredicto por falta de evidencia",
        )
        comprobar(primero["verificacion"]["liberar_pago"] is False, "no se libera pago")
        comprobar(ev1["reto"]["fuente"] == "dns", "la evidencia viene de DNS")
        comprobar(
            ev1["reto"]["servidor"] == f"127.0.0.1:{PUERTO_DNS}",
            "consulta al resolver configurado",
        )
        comprobar(
            ev1["reto"]["detalle"] == "NXDOMAIN",
            f"sin TXT: NXDOMAIN (detalle={ev1['reto']['detalle']})",
        )
        print(f"     nonce emitido: {nonce}")

        print("\n2) Publicación del TXT en el servidor autoritativo")
        registro = f"_agora.{DOMINIO}"
        dns.publicar(registro, f"agora-verify={nonce}")
        print(f"     {registro}  TXT  \"agora-verify={nonce}\"")
        time.sleep(0.2)

        print("\n3) Segunda ejecución con el TXT publicado")
        segundo = requests.post(
            f"http://127.0.0.1:{P_JEFE}/pedido/{job_id}/ejecutar", timeout=120
        ).json()
        ev2 = segundo["verificacion"]["evidencia"]
        comprobar(
            segundo["reto"]["nonce"] == nonce,
            "el reto es idempotente: mismo nonce que se publicó",
        )
        comprobar(ev2["reto"]["ok"] is True, "TXT encontrado y con el valor correcto")
        comprobar(
            ev2["reto"]["valores"] == [f"agora-verify={nonce}"],
            f"valores leídos por DNS: {ev2['reto']['valores']}",
        )
        comprobar(segundo["verificacion"]["modo"] == "llm", "juez con LLM")
        comprobar(segundo["verificacion"]["veredicto"] == "SI", "veredicto SI")
        comprobar(segundo["estado"] == "PAGADO", "pedido PAGADO")
        comprobar(segundo["verificacion"]["reputacion_actual"] == 4.6, "reputación 4.5 -> 4.6")

        print("\n4) DNS público de verdad (resolver del sistema)")
        from agora import evidencia  # se importa aquí: usa el resolver del sistema

        sin_registro = evidencia.txt_dns("toledo-tapas.com", "abc123")
        comprobar(sin_registro["servidor"] == "sistema", "usa el resolver del sistema")
        comprobar(
            sin_registro["detalle"] == "NXDOMAIN",
            f"toledo-tapas.com no existe: {sin_registro['detalle']}",
        )
        comprobar(sin_registro["ok"] is False, "dominio inexistente no aprueba")
        con_otros_txt = evidencia.txt_dns("example.com", "abc123")
        comprobar(
            con_otros_txt["detalle"] == "NoAnswer",
            f"example.com sin _agora: {con_otros_txt['detalle']}",
        )
        comprobar(con_otros_txt["ok"] is False, "dominio sin reto no aprueba")

        print("\n5) Estado final")
        reputacion = requests.get(
            f"http://127.0.0.1:{P_TESTIGO}/reputacion", timeout=10
        ).json()
        print(f"     reputación: {reputacion}")
        comprobar(
            any(t.get("trabajos_ok") == 1 for t in reputacion.values()),
            "un trabajo OK registrado",
        )
    finally:
        for proceso in procesos:
            proceso.terminate()
        for proceso in procesos:
            try:
                proceso.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proceso.kill()
        dns.parar()
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if fallos:
        print(f"FALLARON {len(fallos)} comprobaciones:")
        for fallo in fallos:
            print(f"  - {fallo}")
        return 1
    print("TODO OK: el reto DNS TXT funciona contra DNS real, no solo con la zona de demo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
