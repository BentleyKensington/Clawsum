#!/usr/bin/env bash
# Smoke: one Traefik basic-auth user reaches Grafana/Hermes/Boss/OpenClaw without app login forms.
set -euo pipefail
ENV_FILE=/docker/clawsum/.env
U=$(grep -E '^BOSS_OPS_AUTH_USER=' "$ENV_FILE" | cut -d= -f2- | tr -d '\r')
P=$(grep -E '^BOSS_OPS_AUTH_PASSWORD=' "$ENV_FILE" | cut -d= -f2- | tr -d '\r')
: "${U:?missing BOSS_OPS_AUTH_USER}"
: "${P:?missing BOSS_OPS_AUTH_PASSWORD}"
AUTH=(-u "${U}:${P}")

echo "--- grafana ---"
curl -sk "${AUTH[@]}" -o /dev/null -w "grafana:%{http_code}\n" "https://grafana.clawsum.com/"
curl -sk "${AUTH[@]}" "https://grafana.clawsum.com/api/user"
echo
echo "--- hermes ---"
curl -sk "${AUTH[@]}" -o /dev/null -w "hermes:%{http_code}\n" "https://hermes.clawsum.com/"
curl -sk "${AUTH[@]}" "https://hermes.clawsum.com/api/status" || true
echo
echo "--- boss ---"
curl -sk "${AUTH[@]}" -o /dev/null -w "boss:%{http_code}\n" "https://boss.clawsum.com/"
curl -sk "${AUTH[@]}" "https://boss.clawsum.com/api/auth/get-session" || true
echo
echo "--- openclaw ---"
curl -sk "${AUTH[@]}" -o /dev/null -w "openclaw:%{http_code}\n" "https://openclaw.clawsum.com/"
echo "DONE"
