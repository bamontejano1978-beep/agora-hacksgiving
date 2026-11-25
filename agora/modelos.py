"""Contratos compartidos: los tres servicios hablan el mismo idioma."""

from typing import Literal

from pydantic import BaseModel, Field


class Puja(BaseModel):
    trabajador_id: str
    especialidad: str = "dominios"
    precio: float = Field(gt=0)
    tiempo_min: int = Field(gt=0)
    reputacion: float = Field(ge=1.0, le=5.0)
    score: float | None = None
    desglose: dict[str, float] | None = None


class PedidoEntrada(BaseModel):
    """Acepta texto libre (lo interpreta el agente) o campos explícitos."""

    texto: str | None = Field(default=None, max_length=500)
    pedido: str | None = Field(default=None, max_length=500)
    dominio: str | None = Field(default=None, max_length=253)
    precio_max: float | None = Field(default=None, gt=0, le=100000)


class PujarRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=64)
    dominio: str = Field(min_length=4, max_length=253)


class PujasRespuesta(BaseModel):
    job_id: str
    pujas: list[Puja]


class CompraRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=64)
    dominio: str = Field(min_length=4, max_length=253)
    trabajador_id: str = Field(min_length=1, max_length=64)
    nonce: str | None = Field(default=None, max_length=64)


class CompraRespuesta(BaseModel):
    job_id: str
    trabajador_id: str
    dominio: str
    entrega: str
    simulado: bool
    publicado_en_zona_demo: bool = False
    aviso: str


class RetoRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=64)
    dominio: str = Field(min_length=4, max_length=253)


class Reto(BaseModel):
    job_id: str
    dominio: str
    nonce: str
    registro: str
    valor: str
    expira: str


class VerificacionRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=64)
    dominio: str = Field(min_length=4, max_length=253)
    trabajador_id: str = Field(min_length=1, max_length=64)
    pedido: str = Field(min_length=1, max_length=1000)
    entrega: str = Field(min_length=1, max_length=2000)
    nonce: str | None = Field(default=None, max_length=64)


class VerificacionRespuesta(BaseModel):
    job_id: str
    veredicto: Literal["SI", "NO", "INDETERMINADO"]
    liberar_pago: bool
    modo: Literal["llm", "sin_llm", "evidencia"]
    razon: str
    evidencia: dict
    reputacion_actual: float | None = None
    reputacion_actualizada: bool = False
    aviso: str | None = None


class Pedido(BaseModel):
    """Lo que devuelve `POST /pedido`: el pedido ya adjudicado."""

    job_id: str
    pedido: str
    dominio: str
    precio_max: float
    estado: Literal["ADJUDICADO", "PAGADO", "RECHAZADO", "PENDIENTE"]
    creado: str
    fuente_parseo: str
    ranking: list[Puja] = Field(default_factory=list)
    ganador: Puja | None = None
    razon: str | None = None
    aviso: str | None = None
    # Traza del arco de demo: qué afirmó y qué demostró cada postor, y a quién
    # se pasó el pedido cuando la evidencia no apareció.
    intentos: list[dict] = Field(default_factory=list)
    reasignaciones: list[dict] = Field(default_factory=list)
