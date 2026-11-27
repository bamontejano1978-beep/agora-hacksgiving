# Submission — AGORA (Hacksgiving)

**Preparado:** 2026-11-27. **Estado:** paquete listo para grabar, publicar y enviar. Nada grabado, publicado ni enviado desde esta sesión.

La toma que se envía es la traza real `job-ab8fb180`: **RECHAZADO** porque la evidencia no demostraba control del dominio. No es un fallo oculto: es la garantía del escrow.

## Enlaces

| Campo | Valor |
|---|---|
| Agente | **AGORA — Jefe** |
| Demo en vivo | `https://agora-jefe-b3yds.sprites.app` (pide sesión de Sprite) |
| Auditoría | `https://agora-jefe-b3yds.sprites.app/auditoria` (pide sesión de Sprite) |
| Connector | Sprites OpenRouter `UR-c1YxWmwBnGtohKuC3jQ`; política `sprite_labels: ["agora"]`; endpoints `/v1/chat/completions` y `/v1/models` |
| Modelo | `recursive/flint-v1.0:free` |
| Código | `https://github.com/bamontejano1978-beep/agora-hacksgiving` (comprobar que es público antes de enviar) |
| Vídeo | `<URL_DEL_VÍDEO>` |
| Post | `<URL_DEL_POST>` |

## Respuestas del formulario

- **Nombre:** `<TU_NOMBRE>`
- **Email:** `<TU_EMAIL>`
- **Email de Fly.io:** `<TU_EMAIL_DE_FLY>`
- **Nombre del agente:** `AGORA — Jefe`
- **Connector(es):** `Sprites OpenRouter — UR-c1YxWmwBnGtohKuC3jQ`
- **Código:** `https://github.com/bamontejano1978-beep/agora-hacksgiving`
- **Demo:** `<URL_DEL_VÍDEO>`; live: `https://agora-jefe-b3yds.sprites.app`; auditoría: `https://agora-jefe-b3yds.sprites.app/auditoria`
- **Post:** `<URL_DEL_POST>`

## Descripción (ES)

AGORA es un escrow verificable para agentes: el Jefe interpreta el pedido, convoca pujas, adjudica y solo libera el pago si un Testigo independiente verifica la entrega contra el mundo real mediante un reto DNS TXT. Sin TXT verificado no hay SI; sin SI no se mueve dinero. Todo corre en un Sprite con tres servicios HTTP y un connector de OpenRouter; la clave vive en el connector, no en la máquina.

En la toma `job-ab8fb180`, un trabajador fantasma asegura haber publicado el TXT sin hacerlo: el Jefe lo detecta, reasigna al siguiente perfil y el Testigo real rechaza al segundo trabajador porque el TXT está en la zona DNS de demo y no demuestra control del dominio. El pedido queda RECHAZADO, el pago retenido y la reputación baja a 4.2. La compra y el pago son simulados; el juicio, el escrow, la reputación y la auditoría son reales. Ese NO es la garantía: el escrow no paga sin evidencia verificable. La siguiente iteración es DNS real con DuckDNS.

## Short description (EN)

AGORA is a verifiable escrow for agents. The buyer interprets the job, collects bids, assigns it, and releases payment only when an independent Witness verifies a DNS TXT challenge. No verified TXT, no YES; no YES, no payment. It runs in one Sprite as three HTTP services using an OpenRouter connector; the key stays in the connector.

In run `job-ab8fb180`, a ghost worker claimed to publish the TXT without doing it. The buyer caught it and reassigned. The second worker published in the demo DNS zone, but the real LLM judge said NO because the evidence did not prove control of the domain. The order ended REJECTED, payment held, reputation 4.2. Purchase and payment are simulated; the judgment, escrow, reputation and audit are real. The NO is the guarantee: no verifiable evidence, no money moves.

## La toma que se envía

| Campo | Valor |
|---|---|
| Job | `job-ab8fb180` |
| Fecha | 2026-11-25 13:49 UTC |
| Pedido | «Necesito toledo-tapas.com para el viernes, pago hasta 12 euros» |
| Ganador inicial | `trabajador-fantasma`, 30,13 pts |
| Intento 1 | TXT no observado → NO por evidencia |
| Reasignación | `trabajador-fantasma` → `trabajador-rapido` |
| Intento 2 | TXT observado en zona demo → NO del LLM |
| Razón del LLM | «La evidencia solo muestra un reto TXT publicado, sin demostrar que el trabajador controle el dominio toledo-tapas.com.» |
| Veredicto | NO; `liberar_pago: false` |
| Estado | RECHAZADO |
| Reputación | 4,2 (0 OK, 1 fallo) |

**Por qué es honesto:** la zona DNS es local (`AGORA_DEMO=1`), la compra y el pago son simulados, y el Testigo es un LLM real a través del connector. El vídeo no dice PAGADO. El NO demuestra que el escrow no se fía de la palabra del trabajador.

## Qué es real y qué es simulado

| Pieza | Estado |
|---|---|
| Un Sprite con Jefe, Testigo y Trabajador | **Real** |
| Connector de OpenRouter y modelo `recursive/flint-v1.0:free` | **Real** |
| Juicio del LLM | **Real**; el prompt no dicta el SI |
| Escrow: sin evidencia no hay pago | **Real** |
| Reputación y auditoría | **Real** |
| Compra del dominio | **Simulada** |
| Pago y comisión | **Simulados** |
| Zona DNS de la toma (`AGORA_DEMO=1`) | **Local/simulada**; no es DNS público |
| Mercado abierto de agentes | **No implementado**; la plaza es v2 |

## Post

### X — hilo (el primer post es el enlace del formulario)

**1/3**

> AGORA: un agente solo paga si un Testigo independiente verifica un reto DNS TXT. Un Sprite, 3 servicios, connector de OpenRouter. En esta toma el juez real rechazó la entrega y el escrow no pagó. Compra/pago simulados; juicio real. @flydotio #Hacksgiving

**2/3**

> El fantasma dijo haber publicado el TXT; no lo hizo. El Jefe lo detectó y reasignó. El segundo publicó en la zona de demo, pero el juez real dijo NO: un TXT local no prueba control del dominio. El pedido quedó RECHAZADO.

**3/3**

> Ese NO es la garantía: sin evidencia verificable no se mueve dinero. La compra y el pago son simulados; el escrow, el LLM, la reputación y la auditoría son reales. Vídeo: `<URL_DEL_VÍDEO>` · Código: `<URL_DEL_CODIGO>`

### LinkedIn / Bluesky

> AGORA es un escrow verificable para agentes: el comprador solo paga cuando un Testigo independiente verifica un reto DNS TXT. En la última toma, `job-ab8fb180`, un trabajador fantasma aseguró haber publicado el TXT sin hacerlo; el Jefe lo detectó y reasignó. El segundo trabajador publicó en la zona de demo, pero el juez real rechazó la entrega porque esa evidencia no demostraba control del dominio. El pedido quedó RECHAZADO y el pago retenido: ese NO es la garantía. Todo corre en un Sprite con tres servicios y un connector de OpenRouter. La compra y el pago son simulados; el juicio, el escrow, la reputación y la auditoría son reales. Vídeo: `<URL_DEL_VÍDEO>` · Código: `<URL_DEL_CODIGO>` · @flydotio #Hacksgiving

### Alternativa EN (si el formulario pide inglés)

> AGORA is a verifiable escrow for agents: the buyer pays only when an independent Witness verifies a DNS TXT challenge. In run `job-ab8fb180`, a ghost worker claimed to publish the TXT without doing it; the buyer caught it and reassigned. The second worker published in the demo DNS zone, but the real judge rejected it because the evidence did not prove domain control. The order ended REJECTED and the payment was held. Purchase/payment are simulated; the judgment, escrow, reputation and audit are real. One Sprite, three services, one OpenRouter connector. @flydotio #Hacksgiving · `<URL_DEL_VÍDEO>`

## Checklist antes de enviar

- [ ] Repo con commit final y **público**; el enlace de código abre sin login.
- [ ] Vídeo grabado, subido y con sonido; no dice PAGADO; muestra `job-ab8fb180`.
- [ ] Post publicado con `@flydotio` y enlace al vídeo; `<URL_DEL_POST>` copiado.
- [ ] Formulario: nombre, email, email de Fly.io, agente, connector, código, demo y post.
- [ ] Sin claves en pantalla, repo, vídeo ni post; `openrouter key.txt` sigue fuera.
- [ ] Rotación de la clave decidida (recomendada por OneDrive; no bloquea la submission).
- [ ] Enviado antes del **domingo 29 a las 20:00 CET** (deadline real: domingo 23:59 PST = lunes 08:59 CET).

## Evidencia y fallback

Guardado en local, sin publicar:

- `datos/demo-no.out` — log exacto de la traza.
- `datos/jobs-no.json` — estado de jobs.
- `datos/pedidos-no.json` — estado del pedido, intentos y reasignación.
- `datos/auditoria-no.html` — snapshot de `/auditoria`.
- `datos/demo-no.md` — resumen de la traza.

El vídeo se graba contra el Sprite (`datos/demo-real.out` y `/auditoria` en vivo), no contra la copia local. **No ejecutes `./reiniciar-demo.sh` antes de grabar**: borra la traza viva.

## Límites conocidos

- La compra del dominio y el pago son simulados; no hay registrador ni PSP.
- La zona DNS de esta toma es local; no es DNS público.
- El mercado abierto de agentes no está implementado; es una subasta cerrada entre perfiles de un servicio.
- Sin auth en los endpoints; es una demo, no producción.
- El estado vive en JSON de un solo proceso.

## No hacer

- No decir SI/PAGADO: la traza es NO.
- No resetear ni lanzar otro pedido antes de grabar.
- No usar el stub ni dictar el veredicto.
- No editar `jobs.json`, `pedidos.json` ni el HTML de auditoría.
- No publicar, grabar ni enviar desde esta sesión.

## Pendiente de rellenar

Sustituye `<TU_NOMBRE>`, `<TU_EMAIL>`, `<TU_EMAIL_DE_FLY>`, `<URL_DEL_VÍDEO>`, `<URL_DEL_POST>` y `<URL_DEL_CODIGO>` antes de enviar.
