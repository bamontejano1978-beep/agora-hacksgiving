"""Página de auditoría y evidencia completa en el registro del job.

Cubren lo que pide la auditoría: que el veredicto guarde la evidencia entera y el
reto emitido (para reproducir el `dig`), que la página los enseñe, y que escape
el texto no confiable del trabajador.
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests  # noqa: E402

import jefe  # noqa: E402
import testigo  # noqa: E402
from agora import auditoria  # noqa: E402
from agora.almacen import Almacen  # noqa: E402
from agora.modelos import RetoRequest, VerificacionRequest  # noqa: E402

DOMINIO = "toledo-tapas.com"
NONCE = "9f2c1a7b4e6d8c01"
REGISTRO = f"_agora.{DOMINIO}"
VALOR = f"agora-verify={NONCE}"

EV = {
    "dominio": DOMINIO,
    "dominio_valido": True,
    "ok": True,
    "reto": {
        "ok": True,
        "fuente": "demo",
        "servidor": "sistema",
        "nombre": REGISTRO,
        "esperado": VALOR,
        "valores": [VALOR],
        "detalle": "zona DNS de demo local",
    },
}

RETO = {
    "job_id": "job-1",
    "dominio": DOMINIO,
    "nonce": NONCE,
    "registro": REGISTRO,
    "valor": VALOR,
    "expira": "2026-01-01T00:00:00+00:00",
}

PEDIDO = {
    "job_id": "job-1",
    "pedido": "Comprar toledo-tapas.com",
    "dominio": DOMINIO,
    "precio_max": 12.0,
    "estado": "PAGADO",
    "creado": "2026-11-25T10:00:00+00:00",
    "fuente_parseo": "explicito",
    "ranking": [
        {
            "trabajador_id": "trabajador-dominios",
            "precio": 10.0,
            "tiempo_min": 60,
            "reputacion": 4.5,
            "score": 17.0,
        }
    ],
    "ganador": {"trabajador_id": "trabajador-dominios", "precio": 10.0},
    "razon": "Elegido trabajador-dominios",
    "intentos": [
        {
            "trabajador_id": "trabajador-dominios",
            "resultado": "PAGADO",
            "veredicto": "SI",
            "modo": "llm",
            "liberar_pago": True,
            "evidencia_ok": True,
            "razon": "SI: el TXT esta publicado.",
            "entrega": "Compra simulada y publico el reto TXT",
            "reto": RETO,
            "verificacion": {
                "veredicto": "SI",
                "liberar_pago": True,
                "modo": "llm",
                "razon": "SI: el TXT esta publicado.",
                "evidencia": EV,
            },
        }
    ],
    "reasignaciones": [],
    "reto": RETO,
}

TESTIGO = {
    "jobs": [
        {
            "fecha": "2026-11-25T10:00:05+00:00",
            "job_id": "job-1",
            "dominio": DOMINIO,
            "trabajador": "trabajador-dominios",
            "veredicto": "SI",
            "liberar": True,
            "modo": "llm",
            "evidencia_ok": True,
            "evidencia": EV,
            "reto": RETO,
            "entrega": "Compra simulada y publico el reto TXT",
        }
    ],
    "trabajadores": {
        "trabajador-dominios": {
            "reputacion": 4.6,
            "trabajos_ok": 1,
            "trabajos_fail": 0,
        }
    },
    "retos": {},
}


class TestPagina(unittest.TestCase):
    def test_muestra_pedidos_veredictos_reputacion_y_dig(self):
        html = auditoria.pagina({"job-1": PEDIDO}, TESTIGO)
        for fragmento in (
            "job-1",
            DOMINIO,
            "PAGADO",
            "trabajador-dominios",
            "4.60",
            "dig +short TXT _agora.toledo-tapas.com",
            VALOR,
            "SI",
        ):
            self.assertIn(fragmento, html)

    def test_escapa_el_texto_del_trabajador(self):
        pedido = dict(PEDIDO)
        pedido["intentos"] = [
            dict(PEDIDO["intentos"][0], entrega="<script>alert(1)</script>")
        ]
        html = auditoria.pagina({"job-1": pedido}, TESTIGO)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_sin_datos_avisa_y_sigue(self):
        html = auditoria.pagina({}, None, "No puedo leer el registro del Testigo")
        self.assertIn("No hay pedidos todavía", html)
        self.assertIn("No puedo leer el registro del Testigo", html)
        self.assertIn("Sin reputación registrada", html)

    def test_pedido_antiguo_sin_evidencia_completa(self):
        antiguo = {
            "job_id": "job-2",
            "dominio": DOMINIO,
            "estado": "PENDIENTE",
            "reto": {"registro": REGISTRO, "valor": VALOR},
            "intentos": [
                {
                    "trabajador_id": "trabajador-dominios",
                    "resultado": "PENDIENTE",
                    "veredicto": "NO",
                    "modo": "evidencia",
                    "evidencia_ok": False,
                    "razon": "falta el TXT",
                }
            ],
        }
        html = auditoria.pagina({"job-2": antiguo}, None)
        self.assertIn("Sin evidencia guardada", html)
        self.assertIn("dig +short TXT _agora.toledo-tapas.com", html)


class TestTestigoPersisteEvidencia(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        almacen_original = testigo.almacen
        testigo.almacen = Almacen(os.path.join(self._tmp.name, "jobs.json"))
        self.addCleanup(setattr, testigo, "almacen", almacen_original)

    def test_guarda_evidencia_completa_y_el_reto_emitido(self):
        reto = testigo.crear_reto(RetoRequest(job_id="job-1", dominio=DOMINIO))
        peticion = VerificacionRequest(
            job_id="job-1",
            dominio=DOMINIO,
            trabajador_id="trabajador-dominios",
            pedido="Comprar toledo-tapas.com",
            entrega="Compra simulada y publico el reto TXT",
            nonce=reto.nonce,
        )
        with mock.patch.object(testigo.evidencia, "reunir", return_value=EV), \
                mock.patch.object(testigo.llm, "activo", return_value=True), \
                mock.patch.object(
                    testigo.llm,
                    "chat",
                    return_value='{"veredicto": "SI", "razon": "ok"}',
                ):
            respuesta = testigo.verificar(peticion)

        self.assertTrue(respuesta.liberar_pago)
        datos = testigo.almacen.cargar()
        entrada = datos["jobs"][0]
        self.assertEqual(entrada["evidencia"], EV)
        self.assertEqual(entrada["reto"]["registro"], reto.registro)
        self.assertEqual(entrada["reto"]["valor"], reto.valor)
        self.assertEqual(entrada["entrega"], peticion.entrega)
        self.assertEqual(datos["retos"], {})  # un reto, un uso


class TestEndpointAuditoria(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        almacen_original = jefe.almacen
        jefe.almacen = Almacen(os.path.join(self._tmp.name, "pedidos.json"))
        self.addCleanup(setattr, jefe, "almacen", almacen_original)

    def test_sirve_html_aunque_el_testigo_no_responda(self):
        with mock.patch.object(
            jefe.requests, "get", side_effect=requests.ConnectionError("caido")
        ):
            respuesta = jefe.auditoria_html()
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("text/html", respuesta.media_type)
        self.assertIn(b"No puedo leer el registro del Testigo", respuesta.body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
