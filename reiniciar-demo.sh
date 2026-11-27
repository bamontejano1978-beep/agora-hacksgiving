#!/usr/bin/env bash
# Reinicia AGORA para una toma limpia sin tocar la configuración del gateway.
# Conserva /app/agora-entorno.sh y datos/logs; borra solo el estado de la demo.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$RAIZ" || exit 1

echo "[reinicio] parando servicio agora"
sprite-env services stop agora >/dev/null 2>&1 || true

rm -f "$RAIZ/datos/pedidos.json" "$RAIZ/datos/jobs.json" "$RAIZ/datos/demo_dns.json"

echo "[reinicio] arrancando servicio agora"
sprite-env services start agora >/dev/null 2>&1 || true

for intento in $(seq 1 60); do
  if curl -fsS --max-time 2 http://127.0.0.1:8000/salud >/dev/null 2>&1; then
    echo "[reinicio] jefe OK en :8000"
    echo "  testigo:   $(curl -fsS --max-time 3 http://127.0.0.1:8002/salud 2>/dev/null || echo NO RESPONDE)"
    echo "  trabajador: $(curl -fsS --max-time 3 http://127.0.0.1:8001/salud 2>/dev/null || echo NO RESPONDE)"
    exit 0
  fi
  sleep 0.5
done

echo "[reinicio] el Jefe no responde; revisa /.sprite/logs/services/agora.log"
exit 1
