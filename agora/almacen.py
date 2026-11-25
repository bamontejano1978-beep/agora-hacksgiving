"""Almacén JSON con lock en proceso y escritura atómica.

Límite conocido: el lock protege hilos dentro de un proceso, así que en Fly hay
que correr una sola máquina para el estado (`fly deploy --ha=false`) o mover esto
a una base de datos.
"""

import json
import os
import tempfile
import threading


class Almacen:
    def __init__(self, ruta: str):
        self.ruta = os.path.abspath(ruta)
        self._lock = threading.Lock()

    def _cargar(self) -> dict:
        try:
            with open(self.ruta, encoding="utf-8") as f:
                datos = json.load(f)
            return datos if isinstance(datos, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _guardar(self, datos: dict) -> None:
        directorio = os.path.dirname(self.ruta)
        os.makedirs(directorio, exist_ok=True)
        fd, temporal = tempfile.mkstemp(dir=directorio, prefix=".agora-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporal, self.ruta)  # atómico: nunca deja el JSON a medias
        except BaseException:
            try:
                os.unlink(temporal)
            except OSError:
                pass
            raise

    def cargar(self) -> dict:
        with self._lock:
            return self._cargar()

    def guardar(self, datos: dict) -> dict:
        with self._lock:
            self._guardar(datos)
            return datos

    def actualizar(self, funcion) -> dict:
        """Lee, transforma y guarda bajo el mismo lock."""
        with self._lock:
            datos = self._cargar()
            resultado = funcion(datos)
            if isinstance(resultado, dict):
                datos = resultado
            self._guardar(datos)
            return datos
