# AGORA — escrow verificable para agentes

**El problema:** cuando un agente contrata trabajo a otro, ¿quién comprueba que
está hecho antes de pagar? Confiar en el trabajador es absurdo; confiar en un LLM
también, porque el trabajador controla el texto que lee el LLM.

**AGORA** es un agente comprador (**Jefe**) que interpreta el pedido, convoca
pujas, adjudica por reputación/precio/tiempo y **solo libera el pago si un árbitro
independiente (Testigo) verifica la entrega contra el mundo real**. La prueba de
que un dominio está comprado no es "responde 200": es que el trabajador haya
publicado un **reto DNS TXT** que solo puede crear quien controla la zona.

```
Cliente
   │  "necesito toledo-tapas.com, hasta 12 €"
   ▼
┌───────────────────────────┐        ┌──────────────────────────┐
│ JEFE  (agente comprador)  │──puja──▶│ TRABAJADOR (3 perfiles) │
│ interpreta · adjudica     │◀─pujas──│ precio·tiempo·reputación │
│ paga o no                 │        └──────────────────────────┘
└─────────┬─────────────────┘
          │ 1. pide reto      2. recibe entrega      3. juzga
          ▼
┌───────────────────────────────────────────────────┐
│ TESTIGO  reto DNS TXT · juez LLM                  │
│ sin evidencia no hay SI, y sin SI no hay pago     │
└───────────────────────────────────────────────────┘
```

## Qué es real y qué es simulado

| Pieza | Estado |
|---|---|
| Pujas, adjudicación y estado de pedidos | **Real**: tres servicios HTTP con estado persistido |
| Reto DNS TXT (prueba de control del dominio) | **Real**: `dnspython` contra DNS, o zona local con `AGORA_DEMO=1`. Es la **única** puerta del pago |
| Juicio del LLM | **Real** con OpenRouter (`openrouter/free`), y **no puede pagar sin evidencia** |
| Reputación | **Real**: se persiste y alimenta la siguiente subasta |
| Mercado abierto de agentes | **No implementado**: subasta cerrada entre perfiles de un solo servicio; la plaza es v2 |
| Compra del dominio | **Simulada**: no hay registrador integrado, y `/comprar` lo dice en la respuesta |
| Pago y comisión | **Simulados**: no hay Stripe; el veredicto decide `liberar_pago` |

Que la compra sea simulada es deliberado: lo que se demuestra es el mecanismo de
confianza (evidencia → veredicto → pago), que es la parte difícil.

## Qué es y qué no es

AGORA es un **escrow verificable**: un agente comprador paga solo cuando un
árbitro independiente comprueba la entrega. Hoy hay **un solo tipo de encargo**
(comprar un dominio, con la compra simulada) y **un solo servicio de
trabajadores** con tres perfiles que pujan entre sí.

No es un marketplace de habilidades: **no hay registro ni descubrimiento de
agentes externos**, no se puede pedir una habilidad distinta de la compra de un
dominio y la reputación es global por trabajador, no por habilidad. La plaza de
agentes es **v2**, no está implementada.

## Arranque local

```bash
python -m pip install -r requirements.txt
```

Las variables se leen del entorno (`.env.example` es la referencia; AGORA no
carga `.env` por sí solo: expórtalas o pásalas en la línea de comandos).

Tres terminales (en Windows, Git Bash):

```bash
# 1) Testigo (8002)
AGORA_DEMO=1 python testigo.py

# 2) Trabajador (8001) — necesita el Testigo para leer la reputación
AGORA_DEMO=1 python trabajador.py

# 3) Jefe (8000)
AGORA_DEMO=1 python jefe.py
```

`AGORA_DEMO=1` activa la **zona DNS de demo local** (`datos/demo_dns.json`): el
trabajador "publica" el reto TXT ahí en vez de en DNS real. Es lo que permite
probar el flujo completo sin comprar un dominio. En producción se deja sin
definir y el Testigo consulta DNS de verdad.

## Demo

```bash
python demo_flujo.py
python demo_flujo.py --texto "quiero toledo-tapas.com por 12 euros"
```

Recorre el bucle completo: interpretación del pedido → pujas → adjudicación con
desglose → reto → entrega → veredicto → reputación.

Sin modelo configurado verás `veredicto: INDETERMINADO` y `liberar_pago: false`.
**Eso es correcto**: el modo degradado no mueve dinero. Para el veredicto SI:

```bash
export OPENROUTER_API_KEY=sk-or-...      # o el gateway del connector (ver abajo)
```

Ojo con el tier gratis de OpenRouter: 20 peticiones/minuto y 50/día sin crédito.

## Arco de demo: el trabajador que miente

AGORA no se fía del trabajador, y la forma de demostrarlo es poner uno que
mienta. Con **el mismo valor en Trabajador y Jefe**:

```bash
AGORA_TRABAJADOR_FANTASMA=1 python trabajador.py
AGORA_TRABAJADOR_FANTASMA=1 python jefe.py
```

entra un cuarto perfil, `trabajador-fantasma` (7,50 €, 5 min): puja, gana y en
`/comprar` asegura haber publicado el reto TXT sin publicarlo. La evidencia lo
desmiente, así que el Jefe reasigna el pedido al siguiente perfil del
ranking en la misma llamada a `/ejecutar`, que es quien publica el TXT y cobra.

La respuesta trae `intentos` (lo que afirmó cada perfil, si el TXT se verificó y
su veredicto) y `reasignaciones`, que es la traza que se enseña en la demo:

```
Intento 1: trabajador-fantasma
  afirma:  ... y asegura haber publicado el reto TXT en _agora.toledo-tapas.com
  TXT verificado: False  ->  NO (modo evidencia)
REASIGNACION: trabajador-fantasma no entrego evidencia -> trabajador-rapido
Intento 2: trabajador-rapido
  TXT verificado: True  ->  SI (modo llm)
```

Sin el interruptor no hay cuarto perfil ni reasignación: la falta de
evidencia sigue siendo un `PENDIENTE` reintentable, como antes. El ranking que
se recorre es el original, así que la reasignación es reproducible.

## Página de auditoría

`GET /auditoria` en el Jefe sirve una página HTML con el libro de pedidos
(ranking, estado, ganador y reasignaciones), el historial de veredictos del
Testigo y la reputación. No hay build ni JavaScript: es HTML generado en el
servidor, y todo lo que viene del trabajador o del modelo se escapa.

Cada veredicto guarda la evidencia completa (TXT observados, fuente, detalle) y
el reto emitido, así que la página incluye el comando que lo reproduce:

```bash
dig +short TXT _agora.toledo-tapas.com
```

Ábrela en `http://127.0.0.1:8000/auditoria` (o pídela con `curl`). Si el Testigo
no responde, sigue mostrando los pedidos y avisa de que faltan veredictos y
reputación.

## Probar el reto contra DNS real

`AGORA_DEMO=1` usa una zona local para ensayar sin dominio. El camino real es
`AGORA_DEMO=0`: el Testigo consulta `_agora.<dominio>` TXT contra el resolver del
sistema (o contra el que indiques en `AGORA_DNS_SERVIDOR`).

El flujo tiene dos pasos porque el nonce lo emite el Testigo:

```bash
python demo_flujo.py --esperar-txt
```

1. La primera ejecución **retiene el pago** y devuelve el registro exacto que hay
   que publicar (`reto.registro` y `reto.valor`, más un campo `siguiente` que lo
   dice en castellano).
2. Publicas el TXT, esperas la propagación y repites `POST /pedido/{id}/ejecutar`.
   **El reto es idempotente por pedido**, así que el nonce que publicaste sigue
   siendo el que se verifica. Resultado: `SI`, `PAGADO` y la reputación sube.

Sin ese registro, `/verificar` devuelve NO aunque el modelo diga SI. Un reto
caduca a los 10 minutos y se consume cuando hay veredicto real.

### Opción gratis: DuckDNS (2 minutos)

DuckDNS publica el TXT en el dominio **y en todos sus sub-subdominios**, así que
sirve para `_agora.<tu-subdominio>.duckdns.org`:

```bash
curl -sG "https://www.duckdns.org/update" \
  --data-urlencode "domains=agora-demo" \
  --data-urlencode "token=$DUCKDNS_TOKEN" \
  --data-urlencode "txt=agora-verify=9f2c1a7b4e6d8c01"
# responde OK
```

### Opción con más gancho: dominio propio

`toledo-tapas.com` **está libre** (sin NS ni A, comprobado). Registrarlo y
apuntarlo a Cloudflare (DNS gratis) hace que la historia del vídeo sea literal:
el trabajador entrega `toledo-tapas.com` y publica el TXT. En el panel: registro
`TXT`, nombre `_agora`, valor `agora-verify=<nonce>`.

En ambos casos se comprueba igual:

```bash
dig +short TXT _agora.tu-dominio
```

### Verificación automática sin dominio

```bash
python tests/e2e_dns_real.py
```

Levanta un servidor DNS autoritativo local que habla DNS de verdad (UDP,
consulta/respuesta con dnspython) y recorre el flujo con `AGORA_DEMO=0`:
PENDIENTE sin TXT → se publica → mismo nonce → SI y PAGADO. Además consulta DNS
público real (`toledo-tapas.com` → NXDOMAIN, `example.com` → NoAnswer) para
demostrar que no hay falsos positivos.

## Tests

```bash
python -m unittest discover -s tests -v
```

Cubren lo que puede mover dinero: validación de dominio (IPs, loopback,
`*.internal`), el parser de veredicto (el bug de `startswith("SI")`, que aprobaba
"SIN EMBARGO..."), la regla "sin evidencia o sin LLM no se paga", la propiedad de
que **sin reto no se consulta nada**, la competencia real entre trabajadores y la
escritura atómica del almacén. `tests/test_arco_demo.py` cubre además el
fantasma (no publica de verdad) y la reasignación, y comprueba que sin el
interruptor el flujo de siempre no cambia.

`tests/stub_llm.py` es un LLM falso con forma de OpenRouter para probar el flujo
end-to-end sin gastar créditos:

```bash
PORT=18003 python tests/stub_llm.py
# en las otras terminales:
#   OPENROUTER_BASE_URL=http://127.0.0.1:18003/v1
```

`python tests/e2e_dns_real.py` verifica además el reto contra DNS real (servidor
autoritativo local + consultas al resolver del sistema), sin zona de demo.

## Desplegar en Fly (tres apps)

```bash
fly launch --no-deploy -c fly.testigo.toml
fly volumes create agora_datos --size 1 -r mad
fly deploy -c fly.testigo.toml --ha=false        # estado en JSON: una máquina

fly launch --no-deploy -c fly.trabajador.toml
fly deploy -c fly.trabajador.toml --ha=false

fly launch --no-deploy -c fly.jefe.toml
fly deploy -c fly.jefe.toml --ha=false

fly secrets set OPENROUTER_API_KEY=... -c fly.jefe.toml
fly secrets set OPENROUTER_API_KEY=... -c fly.testigo.toml
```

Los servicios se encuentran por la red privada 6PN, sin exponer el Trabajador ni
el Testigo a internet:

```
http://agora-trabajador.internal:8080
http://agora-testigo.internal:8080
```

`--ha=false` no es un detalle: el estado vive en JSON (con lock en proceso y
escritura atómica). Con dos máquinas tendrías dos reputaciones distintas. Para
varias máquinas, mueve el estado a Postgres.

## Correr el agente en un Sprite con connector

El requisito de Hacksgiving es un agente **en un Sprite** que use **al menos un
connector**. El Jefe es ese agente, y usa el connector de OpenRouter para
interpretar el pedido y para el juicio del Testigo, con la credencial **fuera de
la máquina**.

1. `sprite login` (CLI) o el plugin/MCP de tu agente: `https://sprites.dev/mcp`.
2. En el dashboard de Fly: organización → **Sprites → Connectors → Add connector
   → OpenRouter** (o Anthropic, Ollama Cloud, Pinecone, Firecrawl...).
3. Política de acceso: desactiva *Allow all sprites* y limita por nombre o
   etiqueta. Un connector sin política **deniega todos** los Sprites.
4. Copia la URL del gateway del connector (está en su página de detalle) y úsala
   como base del LLM. **No copies la clave dentro del Sprite.**

```bash
export OPENROUTER_BASE_URL=<gateway-del-connector>
unset OPENROUTER_API_KEY            # no debe estar en el Sprite
python jefe.py & python testigo.py & python trabajador.py &
python demo_flujo.py
```

`agora/llm.py` detecta el modo gateway: si `OPENROUTER_BASE_URL` no es la URL
pública de OpenRouter, considera el LLM activo sin exigir clave local.

## Variables de entorno

| Variable | Defecto | Para qué |
|---|---|---|
| `PORT` | 8000/8001/8002 | puerto de cada servicio |
| `HOST` | `127.0.0.1` | bind local (el contenedor usa `0.0.0.0`) |
| `URL_TRABAJADOR` / `URL_TESTIGO` | localhost | URLs de los otros servicios |
| `OPENROUTER_API_KEY` | vacío | clave directa (no en el repo) |
| `OPENROUTER_BASE_URL` | API pública | gateway de un connector |
| `AGORA_MODELO` | `openrouter/free` | modelo del juicio |
| `AGORA_LLM` | vacío | `off` desactiva el juicio; si hay clave o gateway, se usa |
| `AGORA_DEMO` | `0` | zona DNS de demo local |
| `AGORA_TRABAJADOR_FANTASMA` | `0` | arco de demo: fantasma que miente + reasignación (en Trabajador y Jefe) |
| `JOBS_FILE` / `PEDIDOS_FILE` / `DEMO_DNS_FILE` | `datos/...` | persistencia |
| `AGORA_DNS_SERVIDOR` | sistema | resolver DNS alternativo (`host` o `host:puerto`) |
| `PESO_REPUTACION` / `PESO_PRECIO` / `PESO_TIEMPO` | 0.55/0.30/0.15 | matchmaker |
| `PRECIO_MAX_DEFECTO` | 12 | si el pedido no trae precio |

## Seguridad

- **La clave nunca toca el repo** (`.gitignore`, `.dockerignore`) ni el Sprite
  (connector). Si `openrouter key.txt` estuvo en un repo, una captura o un chat,
  **rótala**: esa clave vale dinero.
- **Sin cliente HTTP hacia el dominio**: el único tráfico saliente es la consulta
  TXT, que no abre conexión al destino. Al no hacer peticiones al dominio no hay
  superficie de SSRF; además el regex rechaza IPs, esquemas, puertos y TLDs
  internos (`.internal`, `.local`).
- **Prompt injection**: la entrega va delimitada y el prompt dice que es dato no
  confiable. Aun así, la defensa real es que el LLM **no puede** abrir el escrow
  sin el reto DNS verificado.
- **Sin auth** en los endpoints: para la demo es aceptable, para producción no.
  Cualquiera puede inflar reputación llamando a `/verificar`.
- El nombre de dominio es del cliente, no del trabajador: el reto prueba control
  del dominio, no que la compra la hiciera ese trabajador concreto.

## Límites conocidos

- La compra de dominios y el pago son **simulados** (no hay registrador ni PSP).
- El lock del almacén es por proceso: una máquina. Con varias, Postgres.
- La prueba demuestra **control** del dominio, no que el trabajador lo haya
  comprado: la compra sigue siendo simulada.
- Los pesos del matchmaker son una política de producto, no una verdad: están en
  variables de entorno para poder discutirlos.
- Es una **subasta cerrada** de un solo tipo de encargo entre perfiles de un
  único servicio. No hay agentes externos, habilidades fuera del reto DNS ni
  reputación por habilidad: eso es la plaza, y la plaza es v2.

## v2: marketplace de habilidades (no implementado)

La plaza queda fuera de esta entrega. Para que AGORA sea un marketplace de
verdad faltan, como mínimo:

- registro y descubrimiento de agentes externos por URL (`POST /agentes`, sonda
  de capacidades, baja y salud);
- pedidos con `habilidad` y filtro duro en la adjudicación;
- una segunda prueba verificable (por ejemplo CNAME), no solo el reto TXT;
- reputación por `(agente, habilidad)`.

Mientras eso no exista, el relato correcto es **escrow verificable**, no
marketplace.

## Checklist de la submission

- [x] Agente que corre (Jefe) y flujo end-to-end ejecutable
- [x] Connector de Sprites soportado por configuración (`OPENROUTER_BASE_URL`)
- [ ] Crear el Sprite y el connector en el dashboard (necesita tu cuenta)
- [ ] Rotar la clave de OpenRouter y sacarla de la carpeta
- [x] `git init` y primer commit (sin `datos/`, sin `.env`, sin la clave)
- [ ] Subir el repo y pegar el enlace en el formulario de Hacksgiving
- [ ] Vídeo de 60-90 s: pedido → pujas → **PENDIENTE sin TXT** → publicas el TXT (30 s) → mismo pedido → **SI y PAGADO** → reputación 4.5 → 4.6
- [ ] Post en X/LinkedIn/Bluesky/Reddit con `@flydotio`
- [ ] Formulario de Hacksgiving antes del 29 de noviembre, medianoche PST
