"""Página de auditoría en HTML, generada en el servidor.

Sin build, sin JavaScript y sin dependencias nuevas: se compone con f-strings y
`html.escape`. La sirve el Jefe, que es el servicio público y ya habla con el
Testigo, dueño del libro de veredictos y de la reputación.

Todo lo que viene del trabajador o del modelo (entrega, razón, valores TXT) se
escapa: la página muestra datos no confiables, no los ejecuta.
"""

from datetime import datetime, timezone
from html import escape

CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; padding: 2.2rem 1.2rem 4rem; background: #fbfaf7; color: #221f1a;
  font: 15px/1.55 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 1100px; margin: 0 auto; }
h1 { margin: 0 0 .25rem; font-size: 1.6rem; letter-spacing: -.01em; }
h2 { margin: 2.6rem 0 .8rem; font-size: 1.12rem; padding-bottom: .35rem;
  border-bottom: 1px solid #e8e2d8; }
h4 { margin: 1.1rem 0 .4rem; font-size: .78rem; text-transform: uppercase;
  letter-spacing: .07em; color: #71685a; }
p { margin: .45rem 0; }
a { color: #7a4b16; }
code { padding: .08rem .3rem; border-radius: 4px; background: #f0eade;
  font: 13px/1.45 ui-monospace, SFMono-Regular, Consolas, monospace; overflow-wrap: anywhere; }
.sub, .muted { color: #71685a; }
.muted { font-size: .88rem; }
table { width: 100%; border-collapse: collapse; font-size: .9rem; }
th, td { padding: .42rem .5rem; text-align: left; vertical-align: top;
  border-bottom: 1px solid #ece6db; }
thead th { font-size: .72rem; text-transform: uppercase; letter-spacing: .05em;
  color: #71685a; }
table.mini { width: auto; min-width: 58%; margin: .2rem 0 .7rem; }
.pill { display: inline-block; padding: .04rem .45rem; border: 1px solid transparent;
  border-radius: 999px; font-size: .74rem; font-weight: 600; }
.pill.ok { background: #e4f4ea; border-color: #bfe2ce; color: #0f6b45; }
.pill.no { background: #fde8e6; border-color: #f5c8c2; color: #a3261b; }
.pill.warn { background: #fdf3dd; border-color: #efdcae; color: #835b0a; }
.pill.info { background: #e8eefb; border-color: #c9d7f2; color: #2b4b8f; }
.stats { display: flex; flex-wrap: wrap; gap: .7rem; margin: 1.3rem 0 .4rem; }
.stats div { min-width: 106px; padding: .65rem .95rem; background: #fff;
  border: 1px solid #e8e2d8; border-radius: 10px; }
.stats .n { display: block; font-size: 1.45rem; font-weight: 700; line-height: 1.2; }
.stats .l { font-size: .72rem; text-transform: uppercase; letter-spacing: .06em;
  color: #71685a; }
details.pedido { margin: .55rem 0; padding: .7rem .95rem; background: #fff;
  border: 1px solid #e8e2d8; border-radius: 10px; }
details.pedido > summary { cursor: pointer; }
details.pedido .cuerpo { margin-top: .65rem; padding-top: .55rem;
  border-top: 1px solid #f0ebe1; }
article.intento { margin: .65rem 0; padding: .15rem .85rem .6rem; background: #fbf8f2;
  border: 1px solid #eee6d9; border-radius: 8px; }
.comando { margin: .35rem 0; }
ul.valores { margin: .15rem 0 .5rem 1.15rem; padding: 0; }
.aviso { margin: .9rem 0; padding: .6rem .85rem; background: #fdf3dd;
  border: 1px solid #efdcae; border-radius: 8px; }
footer { margin-top: 3rem; font-size: .8rem; color: #71685a; }
td.dig-col { min-width: 220px; }
"""

CLASES = {
    "PAGADO": "ok",
    "SI": "ok",
    "RECHAZADO": "no",
    "NO": "no",
    "PENDIENTE": "warn",
    "INDETERMINADO": "warn",
    "ADJUDICADO": "info",
}


def _e(valor) -> str:
    return escape("" if valor is None else str(valor))


def _si_no(valor) -> str:
    return "sí" if bool(valor) else "no"


def _num(valor, decimales: int = 2) -> str:
    try:
        return f"{float(valor):.{decimales}f}"
    except (TypeError, ValueError):
        return "—"


def _euros(valor) -> str:
    numero = _num(valor)
    return "—" if numero == "—" else f"{numero} €"


def _fecha(valor) -> str:
    texto = str(valor or "")
    return texto[:19].replace("T", " ") if texto else "—"


def _pill(valor) -> str:
    clase = CLASES.get(str(valor or "").upper(), "info")
    texto = "—" if valor is None else str(valor)
    return f'<span class="pill {clase}">{_e(texto)}</span>'


def _dig(reto) -> str:
    """El comando que reproduce el reto, más el valor y la caducidad."""
    if not isinstance(reto, dict):
        reto = {}
    registro = reto.get("registro") or reto.get("nombre")
    if not registro:
        return '<p class="muted">Sin reto DNS asociado.</p>'
    valor = reto.get("valor") or reto.get("esperado")
    partes = [f'<p class="comando"><code>dig +short TXT {_e(registro)}</code></p>']
    if valor:
        partes.append(f'<p class="muted">valor esperado: <code>{_e(valor)}</code></p>')
    if reto.get("expira"):
        partes.append(
            f'<p class="muted">caduca: {_e(_fecha(reto.get("expira")))} UTC</p>'
        )
    return "".join(partes)


def _evidencia(ev) -> str:
    if not isinstance(ev, dict) or not ev:
        return (
            '<p class="muted">Sin evidencia guardada '
            "(entrada anterior a esta versión).</p>"
        )
    reto = ev.get("reto") if isinstance(ev.get("reto"), dict) else {}
    filas = [
        ("TXT del reto", _si_no(reto.get("ok"))),
        ("dominio válido", _si_no(ev.get("dominio_valido"))),
        ("fuente", reto.get("fuente") or "—"),
    ]
    if reto.get("servidor"):
        filas.append(("resolver", reto["servidor"]))
    if reto.get("detalle"):
        filas.append(("detalle", reto["detalle"]))
    tabla = '<table class="mini"><tbody>' + "".join(
        f"<tr><th>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in filas
    ) + "</tbody></table>"
    valores = reto.get("valores")
    if isinstance(valores, list) and valores:
        tabla += '<p class="muted">TXT observados:</p><ul class="valores">' + "".join(
            f"<li><code>{_e(v)}</code></li>" for v in valores[:10]
        ) + "</ul>"
    else:
        tabla += '<p class="muted">Sin TXT observados en la consulta.</p>'
    return tabla


def _ranking(pedido: dict) -> str:
    pujas = [p for p in pedido.get("ranking") or [] if isinstance(p, dict)]
    if not pujas:
        return ""
    filas = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            _e(p.get("trabajador_id")),
            _num(p.get("score")),
            _euros(p.get("precio")),
            _e(f"{p.get('tiempo_min')} min"),
            _num(p.get("reputacion")),
        )
        for p in pujas
    )
    return (
        "<h4>Ranking del matchmaker</h4>"
        '<table class="mini"><thead><tr><th>trabajador</th><th>score</th>'
        "<th>precio</th><th>tiempo</th><th>reputación</th></tr></thead>"
        f"<tbody>{filas}</tbody></table>"
    )


def _intento_bloque(numero: int, intento: dict, pedido: dict) -> str:
    verificacion = (
        intento.get("verificacion")
        if isinstance(intento.get("verificacion"), dict)
        else {}
    )
    evidencia = verificacion.get("evidencia")
    reto = intento.get("reto") or pedido.get("reto")
    if not reto and isinstance(evidencia, dict):
        reto = evidencia.get("reto")
    veredicto = intento.get("veredicto") or verificacion.get("veredicto")
    razon = intento.get("razon") or verificacion.get("razon")
    modo = intento.get("modo") or verificacion.get("modo")
    return (
        '<article class="intento">'
        f"<h4>Intento {numero} · {_e(intento.get('trabajador_id'))}</h4>"
        f'<p class="muted">resultado {_pill(intento.get("resultado"))} '
        f"· veredicto {_pill(veredicto)}</p>"
        f'<p><span class="muted">afirma:</span> {_e(intento.get("entrega"))}</p>'
        f'<p><span class="muted">razón del Testigo:</span> {_e(razon)}</p>'
        f'<p class="muted">modo {_e(modo or "—")} · '
        f'pago {_si_no(intento.get("liberar_pago"))}</p>'
        f"{_evidencia(evidencia)}"
        f"{_dig(reto)}"
        "</article>"
    )


def _intentos(pedido: dict) -> str:
    intentos = [i for i in pedido.get("intentos") or [] if isinstance(i, dict)]
    if not intentos:
        veredicto = pedido.get("veredicto")
        if isinstance(veredicto, dict) and veredicto:
            entrega = pedido.get("entrega")
            heredado = {
                "trabajador_id": (pedido.get("ganador") or {}).get("trabajador_id"),
                "resultado": pedido.get("estado"),
                "veredicto": veredicto.get("veredicto"),
                "modo": veredicto.get("modo"),
                "liberar_pago": veredicto.get("liberar_pago"),
                "razon": veredicto.get("razon"),
                "entrega": entrega.get("entrega") if isinstance(entrega, dict) else None,
                "reto": pedido.get("reto"),
                "verificacion": veredicto,
            }
            return (
                '<p class="muted">Pedido anterior a la traza por intentos: '
                "se muestra su último veredicto.</p>"
                + _intento_bloque(1, heredado, pedido)
            )
        reto = pedido.get("reto")
        aviso = '<p class="muted">Todavía no hay intentos de entrega.</p>'
        return aviso + (f"<h4>Reto pendiente</h4>{_dig(reto)}" if reto else "")
    return "".join(
        _intento_bloque(n, intento, pedido) for n, intento in enumerate(intentos, 1)
    )


def _detalle_pedido(pedido: dict) -> str:
    job_id = str(pedido.get("job_id") or "")
    ganador = (pedido.get("ganador") or {}).get("trabajador_id") or "—"
    reasignaciones = [
        r for r in pedido.get("reasignaciones") or [] if isinstance(r, dict)
    ]
    relevos = ""
    if reasignaciones:
        relevos = "<h4>Reasignaciones</h4><ul>" + "".join(
            f"<li>{_e(r.get('de'))} → {_e(r.get('a'))}: {_e(r.get('motivo'))}</li>"
            for r in reasignaciones
        ) + "</ul>"
    aviso = ""
    if pedido.get("aviso"):
        aviso = f'<p class="muted">aviso: {_e(pedido.get("aviso"))}</p>'
    return (
        f'<details class="pedido" id="job-{_e(job_id)}">'
        f"<summary>{_pill(pedido.get('estado'))} "
        f"<strong>{_e(pedido.get('dominio'))}</strong> "
        f"<code>{_e(job_id)}</code> "
        f'<span class="muted">· {_e(_fecha(pedido.get("creado")))} UTC</span>'
        "</summary>"
        '<div class="cuerpo">'
        f"<p>{_e(pedido.get('pedido'))}</p>"
        f'<p class="muted">precio máximo {_e(_euros(pedido.get("precio_max")))} · '
        f"parseo {_e(pedido.get('fuente_parseo'))} · ganador {_e(ganador)}</p>"
        f'<p class="muted">{_e(pedido.get("razon"))}</p>'
        f"{aviso}"
        f"{_ranking(pedido)}"
        f"<h4>Intentos y veredictos</h4>{_intentos(pedido)}"
        f"{relevos}"
        "</div></details>"
    )


def _veredictos(datos, pedidos: dict) -> str:
    jobs = [j for j in (datos or {}).get("jobs") or [] if isinstance(j, dict)]
    if not jobs:
        return '<p class="muted">El Testigo no tiene veredictos registrados.</p>'
    filas = []
    for entrada in reversed(jobs):
        evidencia = (
            entrada.get("evidencia")
            if isinstance(entrada.get("evidencia"), dict)
            else {}
        )
        reto_ev = evidencia.get("reto")
        reto = (
            entrada.get("reto")
            or (reto_ev if isinstance(reto_ev, dict) else {})
            or (pedidos.get(entrada.get("job_id")) or {}).get("reto")
            or {}
        )
        registro = reto.get("registro") or reto.get("nombre")
        esperado = reto.get("valor") or reto.get("esperado")
        dig = f"<code>dig +short TXT {_e(registro)}</code>" if registro else "—"
        if esperado:
            dig += f'<br><span class="muted">esperado</span> <code>{_e(esperado)}</code>'
        detalle = reto_ev.get("detalle") if isinstance(reto_ev, dict) else None
        evidencia_txt = _si_no(entrada.get("evidencia_ok"))
        if detalle:
            evidencia_txt += f'<br><span class="muted">{_e(detalle)}</span>'
        job_id = _e(entrada.get("job_id"))
        if entrada.get("job_id") in pedidos:
            enlace = f'<a href="#job-{job_id}">{job_id}</a>'
        else:
            enlace = f"<code>{job_id}</code>"
        filas.append(
            f"<tr><td>{_e(_fecha(entrada.get('fecha')))}</td><td>{enlace}</td>"
            f"<td>{_e(entrada.get('dominio'))}</td>"
            f"<td>{_e(entrada.get('trabajador'))}</td>"
            f"<td>{_pill(entrada.get('veredicto'))}</td>"
            f"<td>{_e(entrada.get('modo'))}</td>"
            f"<td>{_si_no(entrada.get('liberar'))}</td>"
            f'<td>{evidencia_txt}</td><td class="dig-col">{dig}</td></tr>'
        )
    return (
        "<table><thead><tr><th>fecha (UTC)</th><th>job</th><th>dominio</th>"
        "<th>trabajador</th><th>veredicto</th><th>modo</th><th>pago</th>"
        "<th>evidencia</th><th>reto reproducible</th></tr></thead>"
        f"<tbody>{''.join(filas)}</tbody></table>"
    )


def _clave_reputacion(item) -> float:
    ficha = item[1] if isinstance(item[1], dict) else {}
    try:
        return -float(ficha.get("reputacion") or 0)
    except (TypeError, ValueError):
        return 0.0


def _reputacion(datos) -> str:
    trabajadores = (datos or {}).get("trabajadores") or {}
    if not trabajadores:
        return '<p class="muted">Sin reputación registrada todavía.</p>'
    filas = []
    for nombre, ficha in sorted(trabajadores.items(), key=_clave_reputacion):
        ficha = ficha if isinstance(ficha, dict) else {}
        filas.append(
            f"<tr><td>{_e(nombre)}</td><td>{_num(ficha.get('reputacion'))}</td>"
            f"<td>{_e(ficha.get('trabajos_ok', 0))}</td>"
            f"<td>{_e(ficha.get('trabajos_fail', 0))}</td></tr>"
        )
    return (
        '<table class="mini"><thead><tr><th>trabajador</th><th>reputación</th>'
        "<th>ok</th><th>fallos</th></tr></thead>"
        f"<tbody>{''.join(filas)}</tbody></table>"
    )


def pagina(
    pedidos: dict | None,
    testigo_datos: dict | None = None,
    error_testigo: str | None = None,
) -> str:
    """HTML completo. Si el Testigo falla, la página sigue con los pedidos."""
    pedidos = pedidos if isinstance(pedidos, dict) else {}
    lista = [p for p in pedidos.values() if isinstance(p, dict)]
    lista.sort(key=lambda p: str(p.get("creado") or ""), reverse=True)

    cuenta = {"PAGADO": 0, "PENDIENTE": 0, "RECHAZADO": 0, "ADJUDICADO": 0}
    for pedido in lista:
        estado = str(pedido.get("estado") or "")
        if estado in cuenta:
            cuenta[estado] += 1

    jobs = [j for j in (testigo_datos or {}).get("jobs") or [] if isinstance(j, dict)]
    if error_testigo and not testigo_datos:
        veredictos_html = f'<div class="aviso">{_e(error_testigo)}</div>'
    else:
        veredictos_html = _veredictos(testigo_datos, pedidos)

    pedidos_html = "".join(_detalle_pedido(p) for p in lista)
    if not pedidos_html:
        pedidos_html = '<p class="muted">No hay pedidos todavía.</p>'

    aviso = ""
    if error_testigo and testigo_datos:
        aviso = f'<div class="aviso">{_e(error_testigo)}</div>'

    generado = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AGORA · auditoría</title>
<style>{CSS}</style>
</head>
<body>
<main>
<header>
  <h1>AGORA · auditoría</h1>
  <p class="sub">Escrow verificable por reto DNS TXT: pedidos, veredictos y
  reputación tal como están guardados. Sin build ni JavaScript.</p>
</header>

<div class="stats">
  <div><span class="n">{len(lista)}</span><span class="l">pedidos</span></div>
  <div><span class="n">{cuenta["PAGADO"]}</span><span class="l">pagados</span></div>
  <div><span class="n">{cuenta["PENDIENTE"]}</span><span class="l">pendientes</span></div>
  <div><span class="n">{len(jobs)}</span><span class="l">veredictos</span></div>
</div>

{aviso}
<h2 id="pedidos">Libro de pedidos</h2>
{pedidos_html}

<h2 id="veredictos">Veredictos del Testigo</h2>
{veredictos_html}

<h2 id="reputacion">Reputación</h2>
{_reputacion(testigo_datos)}

<footer>Generado el {generado} UTC · endpoints sin autenticación: es una demo,
no producción. Cada reto incluye el comando <code>dig</code> que lo reproduce.</footer>
</main>
</body>
</html>"""
