#!/usr/bin/env bash
# Arranca Jefe, Testigo y Trabajador dentro de un Sprite y vigila /salud.
# El runtime de Sprite lanza este script como servicio `agora` en cada boot:
# si un proceso muere o deja de responder, el script sale y el runtime lo
# vuelve a arrancar entero.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UVICORN="$RAIZ/.venv/bin/uvicorn"
LOGS="$RAIZ/datos/logs"
mkdir -p "$LOGS"

export AGORA_DEMO="${AGORA_DEMO:-1}"
export AGORA_TRABAJADOR_FANTASMA="${AGORA_TRABAJADOR_FANTASMA:-1}"
export HOST=0.0.0.0
export URL_TRABAJADOR="${URL_TRABAJADOR:-http://127.0.0.1:8001}"
export URL_TESTIGO="${URL_TESTIGO:-http://127.0.0.1:8002}"
export PEDIDOS_FILE="${PEDIDOS_FILE:-$RAIZ/datos/pedidos.json}"
export JOBS_FILE="${JOBS_FILE:-$RAIZ/datos/jobs.json}"
export DEMO_DNS_FILE="${DEMO_DNS_FILE:-$RAIZ/datos/demo_dns.json}"

# Ajustes locales no versionados (por ejemplo OPENROUTER_BASE_URL del connector).
# Vive fuera de datos/ para que un reset de la demo no borre el gateway.
ENTORNO="${AGORA_ENTORNO:-/app/agora-entorno.sh}"
if [ -f "$ENTORNO" ]; then
  . "$ENTORNO"
fi

cd "$RAIZ" || exit 1

pids=()

detener() {
  local p vivo
  for p in "${pids[@]:-}"; do
    [ -n "$p" ] && kill "$p" 2>/dev/null
  done
  for _ in 1 2 3 4 5; do
    vivo=0
    for p in "${pids[@]:-}"; do
      [ -n "$p" ] && kill -0 "$p" 2>/dev/null && vivo=1
    done
    [ "$vivo" -eq 0 ] && break
    sleep 0.4
  done
  for p in "${pids[@]:-}"; do
    [ -n "$p" ] && kill -9 "$p" 2>/dev/null
  done
  wait 2>/dev/null
}

trap 'detener; exit 0' TERM INT
trap detener EXIT

arrancar() {
  local nombre=$1 puerto=$2
  "$UVICORN" "$nombre:app" --host "$HOST" --port "$puerto" \
    >>"$LOGS/$nombre.log" 2>&1 &
  pids+=("$!")
  echo "[arranque] $nombre pid $! en :$puerto"
}

esperar_salud() {
  local nombre=$1 puerto=$2 intento
  for intento in $(seq 1 40); do
    if curl -fsS --max-time 3 "http://127.0.0.1:$puerto/salud" >/dev/null 2>&1; then
      echo "[salud] $nombre OK"
      return 0
    fi
    sleep 0.5
  done
  echo "[salud] $nombre no responde en :$puerto; ultimas lineas del log:"
  tail -n 20 "$LOGS/$nombre.log" 2>/dev/null
  return 1
}

arrancar testigo 8002
arrancar trabajador 8001
arrancar jefe 8000

esperar_salud testigo 8002 || exit 1
esperar_salud trabajador 8001 || exit 1
esperar_salud jefe 8000 || exit 1

echo "[arranque] los tres responden; comprobando /salud cada 20 s"
while true; do
  sleep 20
  for par in "testigo:8002" "trabajador:8001" "jefe:8000"; do
    nombre="${par%:*}"
    puerto="${par#*:}"
    if ! curl -fsS --max-time 3 "http://127.0.0.1:$puerto/salud" >/dev/null 2>&1; then
      echo "[salud] $nombre dejo de responder; salgo para que el runtime reinicie"
      exit 1
    fi
  done
done
