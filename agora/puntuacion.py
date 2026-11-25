"""Matchmaker: elige la mejor puja sin comprar nada.

La fórmula anterior era `reputacion*10 - precio*0.5 - tiempo/60` con datos
hardcodeados: daba 43.00 / 40.83 / 38.50, así que ganaba siempre el mismo
trabajador y la reputación pesaba 20:1 sobre el precio.

Ahora todo se normaliza a 0..1 y se pondera: reputación, precio y tiempo compiten
de verdad. Con los pesos por defecto el ganador cambia según el presupuesto y
según la reputación que el Testigo haya acumulado.
"""

from . import config
from .modelos import Puja


def puntuar(pujas: list[Puja], precio_max: float) -> tuple[list[Puja], list[Puja]]:
    """Devuelve (ranking, descartadas_por_precio). Score 0..100, mayor es mejor."""
    total = (
        config.PESO_REPUTACION + config.PESO_PRECIO + config.PESO_TIEMPO
    ) or 1.0
    peso_rep = config.PESO_REPUTACION / total
    peso_precio = config.PESO_PRECIO / total
    peso_tiempo = config.PESO_TIEMPO / total
    referencia = config.TIEMPO_REFERENCIA_MIN

    ranking: list[Puja] = []
    descartadas: list[Puja] = []
    for puja in pujas:
        if puja.precio > precio_max:
            descartadas.append(puja)
            continue
        parte_rep = peso_rep * (puja.reputacion / 5.0)
        parte_precio = peso_precio * (puja.precio / precio_max)
        parte_tiempo = peso_tiempo * (min(puja.tiempo_min, referencia) / referencia)
        ranking.append(
            puja.model_copy(
                update={
                    "score": round(100 * (parte_rep - parte_precio - parte_tiempo), 2),
                    "desglose": {
                        "reputacion": round(100 * parte_rep, 2),
                        "precio": round(-100 * parte_precio, 2),
                        "tiempo": round(-100 * parte_tiempo, 2),
                    },
                }
            )
        )

    ranking.sort(key=lambda p: (-(p.score or 0), p.precio, p.tiempo_min, p.trabajador_id))
    return ranking, descartadas


def razon(ganador: Puja, descartadas: list[Puja], precio_max: float) -> str:
    desglose = ganador.desglose or {}
    texto = (
        f"Elegido {ganador.trabajador_id} con {ganador.score:.1f} pts: "
        f"reputación {ganador.reputacion:.1f}/5 ({desglose.get('reputacion', 0):+.1f}), "
        f"precio {ganador.precio:.2f} € sobre {precio_max:.2f} € "
        f"({desglose.get('precio', 0):+.1f}), "
        f"{ganador.tiempo_min} min ({desglose.get('tiempo', 0):+.1f})."
    )
    if descartadas:
        fuera = ", ".join(p.trabajador_id for p in descartadas)
        texto += f" Descartadas por precio: {fuera}."
    return texto
