#!/bin/bash
# Unified ops portal: Boss UI + OpenClaw Control UI + Grafana behind Traefik basic auth.
set -euo pipefail

TRAEFIK_DIR="${TRAEFIK_DIR:-/docker/traefik}"
CLAWSUM_DIR="${CLAWSUM_DIR:-/docker/clawsum}"
ENV_FILE="${CLAWSUM_DIR}/.env"

BOSS_HOST="${BOSS_HOST:-boss.srv.example.com}"
OPENCLAW_HOST="${OPENCLAW_HOST:-clawsum.srv.example.com}"
GRAFANA_HOST="${GRAFANA_HOST:-grafana.srv.example.com}"
HERMES_HOST="${HERMES_HOST:-hermes.srv.example.com}"
HERMES_PORT="${HERMES_DASHBOARD_PORT:-9119}"
AUTH_USER="${BOSS_OPS_AUTH_USER:-boss}"
AUTH_PASS="${BOSS_OPS_AUTH_PASSWORD:-}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE" 2>/dev/null || true
  set +a
  BOSS_HOST="${BOSS_UI_HOST:-$BOSS_HOST}"
  OPENCLAW_HOST="${OPENCLAW_UI_HOST:-$OPENCLAW_HOST}"
  GRAFANA_HOST="${GRAFANA_UI_HOST:-$GRAFANA_HOST}"
  HERMES_HOST="${HERMES_UI_HOST:-$HERMES_HOST}"
  AUTH_USER="${BOSS_OPS_AUTH_USER:-$AUTH_USER}"
  AUTH_PASS="${BOSS_OPS_AUTH_PASSWORD:-$AUTH_PASS}"
fi

if [[ -z "$AUTH_PASS" ]]; then
  AUTH_PASS="$(openssl rand -base64 18)"
  echo "Generated BOSS_OPS_AUTH_PASSWORD (save it): ${AUTH_PASS}"
  grep -q '^BOSS_OPS_AUTH_USER=' "$ENV_FILE" 2>/dev/null || echo "BOSS_OPS_AUTH_USER=${AUTH_USER}" >>"$ENV_FILE"
  grep -q '^BOSS_OPS_AUTH_PASSWORD=' "$ENV_FILE" 2>/dev/null \
    && sed -i "s|^BOSS_OPS_AUTH_PASSWORD=.*|BOSS_OPS_AUTH_PASSWORD=${AUTH_PASS}|" "$ENV_FILE" \
    || echo "BOSS_OPS_AUTH_PASSWORD=${AUTH_PASS}" >>"$ENV_FILE"
fi

if ! command -v htpasswd >/dev/null 2>&1; then
  apt-get update -qq && apt-get install -y -qq apache2-utils
fi

HTPASS="$(htpasswd -nbB "$AUTH_USER" "$AUTH_PASS" | sed -e 's/\$/\$\$/g')"

mkdir -p "${TRAEFIK_DIR}/dynamic"

cat > "${TRAEFIK_DIR}/dynamic/ops-portal.yml" <<EOF
http:
  middlewares:
    boss-ops-auth:
      basicAuth:
        users:
          - "${HTPASS}"
    boss-ops-user-header:
      headers:
        customRequestHeaders:
          X-Forwarded-User: "${AUTH_USER}"

  routers:
    clawsum-boss:
      rule: Host(\`${BOSS_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-boss
      middlewares:
        - boss-ops-auth
      tls:
        certResolver: letsencrypt

    clawsum-openclaw:
      rule: Host(\`${OPENCLAW_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-openclaw
      middlewares:
        - boss-ops-auth
        - boss-ops-user-header
      tls:
        certResolver: letsencrypt
      priority: 100

    clawsum-grafana:
      rule: Host(\`${GRAFANA_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-grafana
      middlewares:
        - boss-ops-auth
      tls:
        certResolver: letsencrypt

    clawsum-hermes:
      rule: Host(\`${HERMES_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-hermes
      middlewares:
        - boss-ops-auth
      tls:
        certResolver: letsencrypt

  services:
    clawsum-boss:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:3100
    clawsum-openclaw:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:${OPENCLAW_GATEWAY_PORT:-48166}
    clawsum-grafana:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:3000
    clawsum-hermes:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:${HERMES_PORT}
EOF

# Remove legacy boss-only file if present (ops-portal supersedes)
rm -f "${TRAEFIK_DIR}/dynamic/boss-ui.yml"

COMPOSE="${TRAEFIK_DIR}/docker-compose.yml"
if [[ -f "$COMPOSE" ]] && ! grep -q 'providers.file.directory' "$COMPOSE"; then
  cp "$COMPOSE" "${COMPOSE}.bak.$(date +%Y%m%d)"
  COMPOSE="$COMPOSE" python3 <<'PY'
from pathlib import Path
import os
p = Path(os.environ["COMPOSE"])
text = p.read_text()
needle = "      - --providers.docker.exposedbydefault=false\n"
insert = needle + (
    "      - --providers.file.directory=/dynamic\n"
    "      - --providers.file.watch=true\n"
)
if needle not in text:
    raise SystemExit("Could not patch traefik compose — layout changed")
text = text.replace(needle, insert, 1)
vol = "      - /var/run/docker.sock:/var/run/docker.sock:ro\n"
if "./dynamic:/dynamic:ro" not in text:
    text = text.replace(vol, vol + "      - ./dynamic:/dynamic:ro\n", 1)
p.write_text(text)
PY
fi

# Clawsum .env — public URLs
for kv in "BOSS_UI_HOST=${BOSS_HOST}" "OPENCLAW_UI_HOST=${OPENCLAW_HOST}" "GRAFANA_UI_HOST=${GRAFANA_HOST}" "HERMES_UI_HOST=${HERMES_HOST}"; do
  key="${kv%%=*}"
  grep -q "^${key}=" "$ENV_FILE" 2>/dev/null && sed -i "s|^${key}=.*|${kv}|" "$ENV_FILE" || echo "$kv" >>"$ENV_FILE"
done
if grep -q '^PAPERCLIP_PUBLIC_URL=' "$ENV_FILE" 2>/dev/null; then
  sed -i "s|^PAPERCLIP_PUBLIC_URL=.*|PAPERCLIP_PUBLIC_URL=https://${BOSS_HOST}|" "$ENV_FILE"
else
  echo "PAPERCLIP_PUBLIC_URL=https://${BOSS_HOST}" >>"$ENV_FILE"
fi

cd "$TRAEFIK_DIR"
docker compose up -d

cd "$CLAWSUM_DIR"
docker compose --profile orchestration up -d paperclip
docker compose --profile monitoring up -d grafana 2>/dev/null || true

python3 scripts/patch-control-ui-origins.py 2>/dev/null || true
python3 scripts/patch-control-ui-trusted-proxy.py 2>/dev/null || true
docker compose restart openclaw-gateway 2>/dev/null || true

echo ""
echo "=== Ops portal configured ==="
echo "Boss UI:         https://${BOSS_HOST}"
echo "OpenClaw UI:     https://${OPENCLAW_HOST}"
echo "Grafana:         https://${GRAFANA_HOST}"
echo "Hermes UI:       https://${HERMES_HOST}  (run: bash scripts/hermes-dashboard.sh start)"
echo "Traefik auth:    user=${AUTH_USER}"
echo ""
echo "DNS: A records for boss / clawsum / grafana -> VPS IP"
echo "Test: curl -u ${AUTH_USER}:PASSWORD -sS -o /dev/null -w '%{http_code}\n' https://${BOSS_HOST}/api/health"
echo "Doc:  deploy/docs/BOSS-OPS-PORTAL.md"
