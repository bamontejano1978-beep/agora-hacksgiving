# Guion de la toma NO — AGORA en un Sprite

Toma contra el Sprite, **no contra localhost**. Esta toma **no ejecuta un pedido nuevo**: usa la traza real que ya está en el Sprite, `job-ab8fb180`, **RECHAZADO**.

- URL: `https://agora-jefe-b3yds.sprites.app`
- Auditoría: `https://agora-jefe-b3yds.sprites.app/auditoria`
- La URL pide sesión de Sprite (redirige a `sprites.dev/auth/sprite`); ábrela con tu cuenta antes de grabar.
- Servicio `agora`: Jefe :8000, Testigo :8002, Trabajador :8001 en loopback dentro del Sprite.
- La traza vive en `datos/demo-real.out`, `datos/pedidos.json` y `datos/jobs.json` del Sprite.
- Connector: `UR-c1YxWmwBnGtohKuC3jQ` (Sprites OpenRouter), política `sprite_labels: ["agora"]`; endpoints `/v1/chat/completions` y `/v1/models`. La clave está en el connector, no en el Sprite.
- Modelo: `recursive/flint-v1.0:free`, `modo_llm: gateway`.

## Antes de grabar

1. **No resetees.** `./reiniciar-demo.sh` borra `pedidos.json`, `jobs.json` y `demo_dns.json`: se lleva por delante la traza. **No ejecutes `demo_flujo.py`**: añade otro pedido y gasta cupo del modelo. La toma es la traza actual.
2. **Fallback ya guardado** en local, sin publicar: `datos/demo-no.out`, `datos/jobs-no.json`, `datos/pedidos-no.json`, `datos/auditoria-no.html` y `datos/demo-no.md`.
3. **Comprueba el estado:**

```bash
sprite exec -s agora-jefe --no-stdin -- bash -lc 'cd /app/agora-hacksgiving && curl -sS http://127.0.0.1:8000/salud; echo; curl -sS http://127.0.0.1:8002/; echo; grep -c "job-ab8fb180" datos/jobs.json'
```

Debe salir `llm_activo: true`, `modo_llm: "gateway"`, `modelo: "recursive/flint-v1.0:free"` y `1`.

4. **Abre la URL del Sprite y `/auditoria`** con tu cuenta; deja la pestaña cargada. Comprueba que se ven `job-ab8fb180`, el veredicto NO y la reputación 4,2.
5. **Prepara el terminal** con `sprite exec` (no abras `127.0.0.1` en el navegador): fuente grande, fondo limpio, sin historial con tokens, sin dashboard del connector que muestre una clave, notificaciones silenciadas, 16:9 y 1080p.
6. **No dictes el SI**, no edites JSON/HTML y no cambies al stub. El veredicto es el que es.

## Qué se va a ver

- Un solo Sprite con tres servicios; no localhost.
- El modelo real por el connector `UR-c1YxWmwBnGtohKuC3jQ` (política `sprite_labels: ["agora"]`): `recursive/flint-v1.0:free`; la clave no está en el Sprite.
- `job-ab8fb180`: el fantasma gana la puja y dice haber publicado el TXT sin hacerlo; el Jefe lo detecta y reasigna a `trabajador-rapido`.
- El segundo trabajador publica el TXT en la zona de demo; el Testigo real dice NO porque esa evidencia no demuestra control del dominio.
- Estado **RECHAZADO**, `liberar_pago: false`, reputación **4,2**.
- La auditoría con evidencia, reto, veredicto y reputación.

## Guion (75–90 s)

1. **0–10 s — Qué es.** “AGORA es un escrow verificable: un agente compra, otro trabaja y un Testigo independiente comprueba antes de pagar. Todo en un Sprite, con un connector de OpenRouter.”

2. **10–20 s — El Sprite.** Muestra `https://agora-jefe-b3yds.sprites.app` y la auditoría. “No es localhost: es el Sprite donde corren los tres servicios.”

3. **20–30 s — El modelo y el connector.** Muestra la salida de `/` del Testigo y `/salud`: `modelo: recursive/flint-v1.0:free`, `modo_llm: gateway`, `llm_activo: true`. Di: “El modelo entra por el connector `UR-c1YxWmwBnGtohKuC3jQ`, con política `sprite_labels: ["agora"]` y endpoints `/v1/chat/completions` y `/v1/models`. La clave vive en el connector; el Sprite no la tiene.” Si abres el dashboard del connector, enseña solo nombre, ID y política: nada de claves, tokens ni la pantalla de secrets.

4. **30–55 s — La traza.** Muestra el log real:

```bash
sprite exec -s agora-jefe --no-stdin -- bash -lc 'cd /app/agora-hacksgiving && cat datos/demo-real.out'
```

Narra: pedido → pujas → gana el fantasma → no publica el TXT → NO por evidencia → reasignación → `trabajador-rapido` publica en la zona de demo → el Testigo real decide. Señala estas líneas, que deben verse tal cual:

   - `GANADOR: trabajador-fantasma` con `30.13 pts`.
   - `TXT verificado: False  ->  NO (modo evidencia)`.
   - `REASIGNACION: trabajador-fantasma no entrego evidencia -> trabajador-rapido`.
   - `TXT verificado: True  ->  NO (modo llm)`.
   - `veredicto: NO`, `liberar_pago: False`, `estado del pedido: RECHAZADO`, `reputación de trabajador-rapido: 4.2`.

5. **55–75 s — La auditoría.** Abre `https://agora-jefe-b3yds.sprites.app/auditoria`; enseña `job-ab8fb180`, los dos intentos, el reto `_agora.toledo-tapas.com` (`agora-verify=cd13276584651805`), la evidencia con fuente `demo`, la razón del LLM y la reputación. Anclas que deben aparecer en pantalla: `job-ab8fb180` (×4), `trabajador-fantasma` (×5), `trabajador-rapido` (×8), el reto (×4), `RECHAZADO` (×2) y `4.2`.

6. **75–85 s — El NO.** “El juez real dijo NO porque un TXT en la zona de demo no demuestra que el trabajador controle el dominio. El escrow no pagó.”

7. **85–90 s — Cierre honesto.** “La compra y el pago son simulados; el juicio, el escrow, la reputación y la auditoría son reales. Ese NO es la garantía: sin evidencia verificable, el dinero no se mueve.”

## Qué es real y qué es simulado

**Real**

- El Jefe, el Testigo y el Trabajador como tres servicios HTTP en un Sprite.
- El connector de OpenRouter `UR-c1YxWmwBnGtohKuC3jQ` (política `sprite_labels: ["agora"]`, endpoints `/v1/chat/completions` y `/v1/models`) y el modelo `recursive/flint-v1.0:free`.
- El escrow: sin TXT verificado no hay SI; el código no deja pagar sin evidencia.
- La reputación, el estado persistido y la página de auditoría.

**Simulado**

- La compra del dominio: no hay registrador; `/comprar` lo dice.
- El pago y la comisión: no hay Stripe ni dinero real.
- La zona DNS de esta toma (`AGORA_DEMO=1`): es local y la controla el Testigo; no es DNS público.

**Ojo:** el veredicto de esta traza es **NO**. No digas “PAGADO”. No consultes `_agora.toledo-tapas.com` en DNS público para “demostrarlo”: la fuente es demo y no aparecerá. La prueba es el log y la auditoría del Sprite.

## Contingencia

- **La URL pide login:** entra con tu cuenta de Sprite; el `302` a `sprites.dev/auth/sprite` es normal.
- **El Sprite está frío:** abre la URL antes de grabar; la primera petición puede tardar.
- **La auditoría no carga:** usa el log del paso 4; no inventes ni edites el HTML.
- **El estado ya no está:** no lo reconstruyas a mano. Usa el fallback local solo como referencia y graba el log guardado, explicando que es una traza archivada; no lo presentes como una ejecución nueva.
- **No hay 429:** esta toma no llama al modelo; el juicio ya está hecho.

## No hacer

- No ejecutar `./reiniciar-demo.sh` ni `demo_flujo.py` antes de grabar.
- No usar `http://127.0.0.1:8000` en el navegador.
- No decir SI/PAGADO: el veredicto es NO.
- No usar el stub ni dictar el veredicto.
- No editar `pedidos.json`, `jobs.json` ni el HTML de auditoría.
- No enseñar claves, tokens ni el contenido de `/app/agora-entorno.sh`.
- No grabar, publicar ni enviar desde esta sesión.

## Después de grabar

Para el vídeo, corta a 75–90 s y sube el archivo; no publiques desde esta sesión. El post y las respuestas están en [`SUBMISSION.md`](SUBMISSION.md). Si quieres una toma nueva con DNS real, guárdala para después de esta y no borres el fallback.
