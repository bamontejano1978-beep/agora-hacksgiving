"""Tests reales de lo que puede mover dinero o romper la demo.

Cubren: validación de dominio, parser de veredicto (el bug de `startswith("SI")`),
regla de liberación de pago, competencia entre trabajadores y almacén atómico.
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agora import config, evidencia, puntuacion, veredicto  # noqa: E402
from agora.almacen import Almacen  # noqa: E402
from agora.modelos import Puja  # noqa: E402


def puja(tid: str, precio: float, tiempo: int, reputacion: float) -> Puja:
    return Puja(
        trabajador_id=tid,
        especialidad="dominios",
        precio=precio,
        tiempo_min=tiempo,
        reputacion=reputacion,
    )


class TestDominio(unittest.TestCase):
    def test_acepta_dominios_reales(self):
        for d in ("toledo-tapas.com", "sub.dominio.co.uk", "a.com", "xn--fiqs8s.es"):
            self.assertTrue(evidencia.dominio_valido(d), d)

    def test_rechaza_urls_rutas_puertos_y_huerfanos(self):
        for d in (
            "http://toledo-tapas.com",
            "https://toledo-tapas.com/x",
            "toledo-tapas.com/path",
            "toledo-tapas.com:8080",
            "user@toledo-tapas.com",
            "toledo-tapas.com?x=1",
            "127.0.0.1",
            "169.254.169.254",
            "localhost",
            "testigo.internal",
            "10.0.0.1",
            "",
            "x",
            "dominio-.com",
            "dominio.c",
        ):
            self.assertFalse(evidencia.dominio_valido(d), d)

    def test_normaliza(self):
        self.assertEqual(evidencia.normalizar("  Toledo-Tapas.COM. "), "toledo-tapas.com")


class TestParserVeredicto(unittest.TestCase):
    def test_si_limpio(self):
        self.assertEqual(veredicto.parsear_veredicto("SI"), "SI")

    def test_si_con_tilde_y_coma(self):
        self.assertEqual(veredicto.parsear_veredicto("Sí, cumple."), "SI")

    def test_json(self):
        self.assertEqual(
            veredicto.parsear_veredicto('{"veredicto": "SI", "razon": "ok"}'), "SI"
        )
        self.assertEqual(
            veredicto.parsear_veredicto('{"veredicto": "NO", "razon": "falta"}'), "NO"
        )

    def test_markdown_alrededor(self):
        self.assertEqual(veredicto.parsear_veredicto("**SI** — verificado"), "SI")

    def test_no(self):
        self.assertEqual(veredicto.parsear_veredicto("No cumple el pedido."), "NO")

    def test_sin_embargo_no_es_un_si(self):
        """EL BUG: startswith("SI") aprobaba esto."""
        texto = (
            "SIN EMBARGO, la evidencia muestra que el dominio no está registrado "
            "y no hay TXT publicado para el reto emitido."
        )
        self.assertIsNone(veredicto.parsear_veredicto(texto))

    def test_texto_inconcluyente(self):
        self.assertIsNone(veredicto.parsear_veredicto("quizá, depende del día"))
        self.assertIsNone(veredicto.parsear_veredicto(""))
        self.assertIsNone(veredicto.parsear_veredicto(None))


class TestReglaDePago(unittest.TestCase):
    def test_sin_evidencia_no_hay_pago_aunque_el_llm_diga_si(self):
        d = veredicto.decidir(evidencia_ok=False, texto_llm="SI", llm_activo=True)
        self.assertEqual(d["veredicto"], "NO")
        self.assertFalse(d["liberar_pago"])
        self.assertEqual(d["modo"], "evidencia")

    def test_sin_llm_no_hay_pago(self):
        d = veredicto.decidir(evidencia_ok=True, texto_llm=None, llm_activo=False)
        self.assertEqual(d["veredicto"], "INDETERMINADO")
        self.assertFalse(d["liberar_pago"])
        self.assertEqual(d["modo"], "sin_llm")

    def test_evidencia_y_si_libera(self):
        d = veredicto.decidir(evidencia_ok=True, texto_llm="SI", llm_activo=True)
        self.assertEqual(d["veredicto"], "SI")
        self.assertTrue(d["liberar_pago"])

    def test_sin_embargo_no_libera(self):
        d = veredicto.decidir(
            evidencia_ok=True,
            texto_llm="SIN EMBARGO, el dominio no está registrado",
            llm_activo=True,
        )
        self.assertFalse(d["liberar_pago"])

    def test_inconcluyente_no_libera(self):
        d = veredicto.decidir(
            evidencia_ok=True, texto_llm="depende del día", llm_activo=True
        )
        self.assertFalse(d["liberar_pago"])
        self.assertEqual(d["veredicto"], "INDETERMINADO")


class TestPuntuacion(unittest.TestCase):
    PUJAS = [
        puja("trabajador-dominios", 10.0, 60, 4.9),
        puja("trabajador-rapido", 12.0, 10, 4.7),
        puja("trabajador-barato", 9.0, 120, 4.5),
    ]

    def test_hay_competencia_real(self):
        ranking, descartadas = puntuacion.puntuar(self.PUJAS, 12.0)
        self.assertEqual(len(ranking), 3)
        self.assertEqual(descartadas, [])
        # Antes la fórmula daba 43/40.83/38.5: siempre el mismo ganador.
        self.assertEqual(ranking[0].trabajador_id, "trabajador-dominios")
        self.assertLess(ranking[0].score - ranking[1].score, 5.0)  # reñido

    def test_reputacion_cambia_el_ganador(self):
        pujas = [
            puja("trabajador-dominios", 10.0, 60, 4.6),  # tras un fallo
            puja("trabajador-rapido", 12.0, 10, 4.7),
            puja("trabajador-barato", 9.0, 120, 4.5),
        ]
        ranking, _ = puntuacion.puntuar(pujas, 12.0)
        self.assertEqual(ranking[0].trabajador_id, "trabajador-rapido")

    def test_respeta_el_presupuesto(self):
        ranking, descartadas = puntuacion.puntuar(self.PUJAS, 10.0)
        self.assertNotIn("trabajador-rapido", [p.trabajador_id for p in ranking])
        self.assertEqual([p.trabajador_id for p in descartadas], ["trabajador-rapido"])
        self.assertTrue(all(p.precio <= 10.0 for p in ranking))

    def test_sin_pujas_en_presupuesto(self):
        ranking, descartadas = puntuacion.puntuar(self.PUJAS, 8.5)
        self.assertEqual(ranking, [])
        self.assertEqual(len(descartadas), 3)

    def test_no_muta_las_pujas_de_entrada(self):
        original = puja("trabajador-dominios", 10.0, 60, 4.9)
        puntuacion.puntuar([original], 12.0)
        self.assertIsNone(original.score)


class TestAlmacen(unittest.TestCase):
    def test_roundtrip_y_directorio_creado(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "sub", "datos.json")
            almacen = Almacen(ruta)
            self.assertEqual(almacen.cargar(), {})
            almacen.guardar({"a": 1})
            self.assertEqual(almacen.cargar(), {"a": 1})

    def test_actualizar_bajo_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            almacen = Almacen(os.path.join(tmp, "d.json"))
            almacen.guardar({"n": 0})

            def _sumar(datos):
                datos["n"] = datos.get("n", 0) + 1
                return datos

            for _ in range(5):
                almacen.actualizar(_sumar)
            self.assertEqual(almacen.cargar()["n"], 5)

    def test_no_deja_temporales(self):
        with tempfile.TemporaryDirectory() as tmp:
            almacen = Almacen(os.path.join(tmp, "d.json"))
            almacen.guardar({"x": 1})
            self.assertEqual([f for f in os.listdir(tmp) if f.endswith(".tmp")], [])

    def test_json_corrupto_no_revienta(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "d.json")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("{ esto no es json")
            self.assertEqual(Almacen(ruta).cargar(), {})


class TestEvidencia(unittest.TestCase):
    def test_sin_reto_no_se_consulta_nada(self):
        """Sin nonce no hay nada que probar: ni DNS, ni red, ni datos de apoyo."""
        ev = evidencia.reunir("toledo-tapas.com", None)
        self.assertFalse(ev["ok"])
        self.assertFalse(ev["reto"]["ok"])
        self.assertEqual(set(ev), {"dominio", "dominio_valido", "ok", "reto"})

    def test_dominio_invalido_no_consulta_nada(self):
        ev = evidencia.reunir("http://169.254.169.254", "abc")
        self.assertFalse(ev["ok"])
        self.assertFalse(ev["dominio_valido"])

    def test_publicar_y_verificar_reto(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "zona.json")
            with mock.patch.object(config, "DEMO_DNS_FILE", ruta), mock.patch.object(
                config, "DEMO", True
            ):
                self.assertFalse(evidencia.txt_demo("toledo-tapas.com", "abc123")["ok"])
                evidencia.publicar_txt_demo("toledo-tapas.com", "abc123")
                evidencia.publicar_txt_demo("toledo-tapas.com", "abc123")  # idempotente
                self.assertTrue(evidencia.txt_demo("toledo-tapas.com", "abc123")["ok"])
                self.assertFalse(evidencia.txt_demo("toledo-tapas.com", "otro")["ok"])
                self.assertTrue(evidencia.reunir("toledo-tapas.com", "abc123")["ok"])
                zona = Almacen(ruta).cargar()
                self.assertEqual(len(zona["toledo-tapas.com"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
