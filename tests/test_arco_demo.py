"""Arco de demo de dos actos: el trabajador fantasma y la reasignación.

Acto 1: `trabajador-fantasma` puja barato, gana y asegura haber publicado el
reto TXT. No lo publica: el Testigo no ve evidencia y no paga.
Acto 2: en la misma llamada a /ejecutar, el Jefe reasigna al siguiente postor
del ranking, que sí publica y cobra.

Todo esto es opt-in con AGORA_TRABAJADOR_FANTASMA=1. Sin el interruptor, el
camino feliz y el PENDIENTE reintentable quedan exactamente igual.
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402

import jefe  # noqa: E402
import trabajador  # noqa: E402
from agora import config, puntuacion  # noqa: E402
from agora.almacen import Almacen  # noqa: E402
from agora.modelos import CompraRequest, PedidoEntrada, PujarRequest  # noqa: E402

DOMINIO = "toledo-tapas.com"
NONCE = "9f2c1a7b4e6d8c01"
FANTASMA = trabajador.FANTASMA


def _puja(tid: str, precio: float, tiempo: int, reputacion: float = 4.5) -> dict:
    return {
        "trabajador_id": tid,
        "especialidad": "dominios",
        "precio": precio,
        "tiempo_min": tiempo,
        "reputacion": reputacion,
    }


PUJAS_REALES = [
    _puja("trabajador-dominios", 10.0, 60),
    _puja("trabajador-rapido", 12.0, 10),
    _puja("trabajador-barato", 9.0, 120),
]
PUJAS_CON_FANTASMA = [_puja(FANTASMA, 7.5, 5)] + PUJAS_REALES


def _veredicto_sin_evidencia() -> dict:
    return {
        "veredicto": "NO",
        "liberar_pago": False,
        "modo": "evidencia",
        "razon": "La evidencia no demuestra control del dominio: falta el TXT.",
        "evidencia": {"ok": False, "reto": {"ok": False, "detalle": "sin TXT"}},
    }


def _veredicto_pagado() -> dict:
    return {
        "veredicto": "SI",
        "liberar_pago": True,
        "modo": "llm",
        "razon": "SI: el TXT del reto esta publicado.",
        "evidencia": {"ok": True, "reto": {"ok": True}},
    }


class Servicios:
    """Sustituye a `jefe._post`: contesta como el Trabajador y el Testigo."""

    def __init__(self, pujas: list[dict], veredictos: list[dict]):
        self.pujas = pujas
        self.veredictos = list(veredictos)
        self.compras: list[str] = []
        self.llamadas: list[str] = []

    def __call__(self, url: str, payload: dict, timeout: float = 30.0) -> dict:
        self.llamadas.append(url)
        if url.endswith("/pujar"):
            return {"job_id": payload["job_id"], "pujas": self.pujas}
        if url.endswith("/reto"):
            return {
                "job_id": payload["job_id"],
                "dominio": payload["dominio"],
                "nonce": NONCE,
                "registro": f"_agora.{payload['dominio']}",
                "valor": f"agora-verify={NONCE}",
                "expira": "2099-01-01T00:00:00+00:00",
            }
        if url.endswith("/comprar"):
            self.compras.append(payload["trabajador_id"])
            return {
                "job_id": payload["job_id"],
                "trabajador_id": payload["trabajador_id"],
                "dominio": payload["dominio"],
                "entrega": f"compra simulada por {payload['trabajador_id']}",
                "simulado": True,
                "publicado_en_zona_demo": payload["trabajador_id"] != FANTASMA,
                "aviso": "simulacion",
            }
        if url.endswith("/verificar"):
            if not self.veredictos:
                raise AssertionError("el Jefe verifico mas veces de las previstas")
            return self.veredictos.pop(0)
        raise AssertionError(f"llamada inesperada: {url}")


class TestJefeReasigna(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        almacen_original = jefe.almacen
        jefe.almacen = Almacen(os.path.join(self._tmp.name, "pedidos.json"))
        self.addCleanup(setattr, jefe, "almacen", almacen_original)

    def _crear(self, servicios: Servicios) -> dict:
        with mock.patch.object(jefe, "_post", servicios):
            pedido = jefe.crear_pedido(
                PedidoEntrada(
                    dominio=DOMINIO, precio_max=12.0, pedido="comprar el dominio"
                )
            )
        return pedido.model_dump(mode="json")

    def _ejecutar(self, job_id: str, servicios: Servicios) -> dict:
        with mock.patch.object(jefe, "_post", servicios):
            return jefe.ejecutar(job_id)

    def test_sin_interruptor_el_camino_feliz_y_el_reintento_siguen_igual(self):
        with mock.patch.object(config, "TRABAJADOR_FANTASMA", False):
            s = Servicios(
                PUJAS_REALES, [_veredicto_sin_evidencia(), _veredicto_pagado()]
            )
            pedido = self._crear(s)
            primero = self._ejecutar(pedido["job_id"], s)

            self.assertEqual(primero["estado"], "PENDIENTE")
            self.assertEqual(primero["reasignaciones"], [])
            self.assertEqual(len(primero["intentos"]), 1)
            self.assertEqual(s.compras, [pedido["ganador"]["trabajador_id"]])

            segundo = self._ejecutar(pedido["job_id"], s)
            self.assertEqual(segundo["estado"], "PAGADO")
            self.assertEqual(segundo["reasignaciones"], [])
            self.assertEqual(
                segundo["pedido"]["ganador"]["trabajador_id"],
                pedido["ganador"]["trabajador_id"],
            )

    def test_con_interruptor_reasigna_y_paga_al_siguiente_en_la_misma_llamada(self):
        with mock.patch.object(config, "TRABAJADOR_FANTASMA", True):
            s = Servicios(
                PUJAS_CON_FANTASMA,
                [_veredicto_sin_evidencia(), _veredicto_pagado()],
            )
            pedido = self._crear(s)
            self.assertEqual(pedido["ganador"]["trabajador_id"], FANTASMA)

            resultado = self._ejecutar(pedido["job_id"], s)
            relevo = resultado["reasignaciones"][0]["a"]

            self.assertEqual(resultado["estado"], "PAGADO")
            self.assertEqual(
                [i["trabajador_id"] for i in resultado["intentos"]],
                [FANTASMA, relevo],
            )
            self.assertEqual(s.compras, [FANTASMA, relevo])
            self.assertFalse(resultado["intentos"][0]["evidencia_ok"])
            self.assertFalse(resultado["intentos"][0]["liberar_pago"])
            # La evidencia completa y el reto emitido viajan con cada intento.
            self.assertFalse(
                resultado["intentos"][0]["verificacion"]["evidencia"]["reto"]["ok"]
            )
            self.assertTrue(resultado["intentos"][0]["reto"]["registro"].startswith("_agora."))
            self.assertTrue(resultado["intentos"][1]["liberar_pago"])
            self.assertEqual(
                resultado["reasignaciones"],
                [
                    {
                        "de": FANTASMA,
                        "a": relevo,
                        "motivo": "sin evidencia: el reto TXT no se publico",
                    }
                ],
            )
            self.assertEqual(resultado["pedido"]["ganador"]["trabajador_id"], relevo)
            self.assertEqual(s.veredictos, [])

    def test_si_se_acaban_los_postores_el_pedido_se_rechaza(self):
        with mock.patch.object(config, "TRABAJADOR_FANTASMA", True):
            s = Servicios([_puja(FANTASMA, 7.5, 5)], [_veredicto_sin_evidencia()])
            pedido = self._crear(s)

            resultado = self._ejecutar(pedido["job_id"], s)
            self.assertEqual(resultado["estado"], "RECHAZADO")
            self.assertEqual(len(resultado["intentos"]), 1)
            self.assertEqual(s.veredictos, [])

            with self.assertRaises(HTTPException) as ctx:
                self._ejecutar(pedido["job_id"], s)
            self.assertEqual(ctx.exception.status_code, 409)


class TestTrabajadorFantasma(unittest.TestCase):
    def test_solo_puja_con_el_interruptor_y_gana_la_subasta(self):
        with mock.patch.object(trabajador, "_reputaciones", return_value={}):
            with mock.patch.object(config, "TRABAJADOR_FANTASMA", False):
                sin = trabajador.pujar(PujarRequest(job_id="job-x", dominio=DOMINIO))
                self.assertNotIn(FANTASMA, [p.trabajador_id for p in sin.pujas])
            with mock.patch.object(config, "TRABAJADOR_FANTASMA", True):
                con = trabajador.pujar(PujarRequest(job_id="job-x", dominio=DOMINIO))

        self.assertIn(FANTASMA, [p.trabajador_id for p in con.pujas])
        ranking, _ = puntuacion.puntuar(con.pujas, 12.0)
        self.assertEqual(ranking[0].trabajador_id, FANTASMA)

    def test_afirma_que_publica_pero_no_llama_al_testigo(self):
        peticion = CompraRequest(
            job_id="job-x", dominio=DOMINIO, trabajador_id=FANTASMA, nonce=NONCE
        )
        with mock.patch.object(config, "DEMO", True), mock.patch.object(
            config, "TRABAJADOR_FANTASMA", True
        ), mock.patch.object(trabajador.requests, "post") as post:
            respuesta = trabajador.comprar(peticion)

        post.assert_not_called()
        self.assertFalse(respuesta.publicado_en_zona_demo)
        self.assertIn("asegura haber publicado", respuesta.entrega)

    def test_un_trabajador_normal_sigue_publicando(self):
        peticion = CompraRequest(
            job_id="job-x",
            dominio=DOMINIO,
            trabajador_id="trabajador-dominios",
            nonce=NONCE,
        )
        with mock.patch.object(config, "DEMO", True), mock.patch.object(
            trabajador.requests, "post"
        ) as post:
            post.return_value.ok = True
            post.return_value.json.return_value = {"publicado": True}
            respuesta = trabajador.comprar(peticion)

        post.assert_called_once()
        self.assertTrue(respuesta.publicado_en_zona_demo)


if __name__ == "__main__":
    unittest.main(verbosity=2)
