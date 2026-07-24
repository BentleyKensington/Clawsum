#!/usr/bin/env bash
# Configure clawsum.com marketing + ops subdomains on Traefik (reference VPS).
set -euo pipefail

TRAEFIK_DIR="${TRAEFIK_DIR:-/docker/traefik}"
CLAWSUM_DIR="${CLAWSUM_DIR:-/docker/clawsum}"
ENV_FILE="${CLAWSUM_DIR}/.env"
SITE_SRC="${CLAWSUM_DIR}/sites/clawsum-com"
SITE_DST="${CLAWSUM_DIR}/data/sites/clawsum-com"
MARKETING_PORT="${MARKETING_PORT:-8088}"

DOMAIN="${CLAWSUM_DOMAIN:-clawsum.com}"
# Prefer clawsum.com map; allow override only if already on this domain
BOSS_HOST="boss.${DOMAIN}"
OPENCLAW_HOST="openclaw.${DOMAIN}"
GRAFANA_HOST="grafana.${DOMAIN}"
HERMES_HOST="hermes.${DOMAIN}"
LOGIN_HOST="login.${DOMAIN}"
CONNECT_HOST="connect.${DOMAIN}"
WWW_HOST="www.${DOMAIN}"
HERMES_PORT="${HERMES_DASHBOARD_PORT:-9119}"
OPENCLAW_PORT="${OPENCLAW_GATEWAY_PORT:-48166}"
AUTH_USER="${BOSS_OPS_AUTH_USER:-boss}"
AUTH_PASS="${BOSS_OPS_AUTH_PASSWORD:-}"

if [[ -f "$ENV_FILE" ]]; then
  # Load KEY=VALUE without `source` (avoids .env side effects / nounset traps)
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" == *"="* ]] || continue
    key="${line%%=*}"
    val="${line#*=}"
    key="${key%"${key##*[![:space:]]}"}"
    val="${val#\"}"; val="${val%\"}"
    val="${val#\'}"; val="${val%\'}"
    export "$key=$val"
  done < "$ENV_FILE"
  # Keep ports/auth from .env; force clawsum.com hostnames unless FORCE_LEGACY_HOSTS=1
  if [[ "${FORCE_LEGACY_HOSTS:-}" != "1" ]]; then
    BOSS_HOST="boss.${DOMAIN}"
    OPENCLAW_HOST="openclaw.${DOMAIN}"
    GRAFANA_HOST="grafana.${DOMAIN}"
    HERMES_HOST="hermes.${DOMAIN}"
    LOGIN_HOST="login.${DOMAIN}"
    CONNECT_HOST="connect.${DOMAIN}"
  else
    BOSS_HOST="${BOSS_UI_HOST:-$BOSS_HOST}"
    OPENCLAW_HOST="${OPENCLAW_UI_HOST:-$OPENCLAW_HOST}"
    GRAFANA_HOST="${GRAFANA_UI_HOST:-$GRAFANA_HOST}"
    HERMES_HOST="${HERMES_UI_HOST:-$HERMES_HOST}"
    LOGIN_HOST="${LOGIN_UI_HOST:-$LOGIN_HOST}"
    CONNECT_HOST="${CONNECT_UI_HOST:-$CONNECT_HOST}"
  fi
  HERMES_PORT="${HERMES_DASHBOARD_PORT:-$HERMES_PORT}"
  OPENCLAW_PORT="${OPENCLAW_GATEWAY_PORT:-$OPENCLAW_PORT}"
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

HTPASS_FILE="${TRAEFIK_DIR}/dynamic/clawsum-ops.htpasswd"
htpasswd -nbB "$AUTH_USER" "$AUTH_PASS" | tr -d '\r' > "$HTPASS_FILE"
chmod 644 "$HTPASS_FILE"

mkdir -p "$SITE_DST"
if [[ -d "$SITE_SRC" ]]; then
  cp -a "$SITE_SRC/." "$SITE_DST/"
elif [[ -d "${CLAWSUM_DIR}/deploy/sites/clawsum-com" ]]; then
  cp -a "${CLAWSUM_DIR}/deploy/sites/clawsum-com/." "$SITE_DST/"
else
  echo "ERROR: sites/clawsum-com not found under ${CLAWSUM_DIR}" >&2
  exit 1
fi

docker rm -f clawsum-marketing 2>/dev/null || true
docker run -d --name clawsum-marketing --restart unless-stopped \
  -p "127.0.0.1:${MARKETING_PORT}:8080" \
  -v "${SITE_DST}:/usr/share/nginx/html:ro" \
  -v "${SITE_DST}/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:1.27-alpine

MARKETING_URL="http://127.0.0.1:${MARKETING_PORT}"
sleep 1
curl -sf "${MARKETING_URL}/" >/dev/null || {
  echo "ERROR: marketing nginx not responding on ${MARKETING_URL}" >&2
  docker logs clawsum-marketing 2>&1 | tail -20
  exit 1
}

mkdir -p "${TRAEFIK_DIR}/dynamic"
cat > "${TRAEFIK_DIR}/dynamic/clawsum-com.yml" <<EOF
http:
  middlewares:
    clawsum-ops-auth:
      basicAuth:
        usersFile: /dynamic/clawsum-ops.htpasswd
    clawsum-ops-user-header:
      headers:
        customRequestHeaders:
          X-Forwarded-User: "${AUTH_USER}"
    hermes-host-rewrite:
      headers:
        customRequestHeaders:
          Host: "127.0.0.1:${HERMES_PORT}"

  routers:
    clawsum-marketing:
      rule: Host(\`${DOMAIN}\`) || Host(\`${WWW_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-marketing
      tls:
        certResolver: letsencrypt
      priority: 10

    clawsum-login:
      rule: Host(\`${LOGIN_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-marketing
      middlewares:
        - clawsum-ops-auth
      tls:
        certResolver: letsencrypt

    clawsum-connect:
      rule: Host(\`${CONNECT_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-marketing
      middlewares:
        - clawsum-ops-auth
      tls:
        certResolver: letsencrypt

    clawsum-boss:
      rule: Host(\`${BOSS_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-boss
      middlewares:
        - clawsum-ops-auth
      tls:
        certResolver: letsencrypt

    clawsum-openclaw:
      rule: Host(\`${OPENCLAW_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-openclaw
      middlewares:
        - clawsum-ops-auth
        - clawsum-ops-user-header
      tls:
        certResolver: letsencrypt
      priority: 100

    clawsum-grafana:
      rule: Host(\`${GRAFANA_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-grafana
      middlewares:
        - clawsum-ops-auth
      tls:
        certResolver: letsencrypt

    clawsum-hermes:
      rule: Host(\`${HERMES_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-hermes
      middlewares:
        - clawsum-ops-auth
        - hermes-host-rewrite
      tls:
        certResolver: letsencrypt

  services:
    clawsum-marketing:
      loadBalancer:
        servers:
          - url: ${MARKETING_URL}
    clawsum-boss:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:3100
    clawsum-openclaw:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:${OPENCLAW_PORT}
    clawsum-grafana:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:3000
    clawsum-hermes:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:${HERMES_PORT}
EOF

rm -f "${TRAEFIK_DIR}/dynamic/boss-ui.yml"
if [[ -f "${TRAEFIK_DIR}/dynamic/ops-portal.yml" ]]; then
  mv "${TRAEFIK_DIR}/dynamic/ops-portal.yml" "${TRAEFIK_DIR}/dynamic/ops-portal.yml.bak.$(date +%Y%m%d%H%M)" || true
fi

touch "$ENV_FILE"
for kv in \
  "TRAEFIK_HOST=${DOMAIN}" \
  "BOSS_UI_HOST=${BOSS_HOST}" \
  "OPENCLAW_UI_HOST=${OPENCLAW_HOST}" \
  "GRAFANA_UI_HOST=${GRAFANA_HOST}" \
  "HERMES_UI_HOST=${HERMES_HOST}" \
  "LOGIN_UI_HOST=${LOGIN_HOST}" \
  "CONNECT_UI_HOST=${CONNECT_HOST}" \
  "PAPERCLIP_PUBLIC_URL=https://${BOSS_HOST}" \
  "CLAWSUM_BOSS_URL=https://${BOSS_HOST}" \
  "CLAWSUM_OPENCLAW_URL=https://${OPENCLAW_HOST}" \
  "CLAWSUM_GRAFANA_URL=https://${GRAFANA_HOST}" \
  "CLAWSUM_HERMES_URL=https://${HERMES_HOST}"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^${key}=.*|${kv}|" "$ENV_FILE"
  else
    echo "$kv" >>"$ENV_FILE"
  fi
done

cd "$TRAEFIK_DIR"
# .env may set COMPOSE_PROJECT_NAME=clawsum — do not attach Traefik to that project
env -u COMPOSE_PROJECT_NAME COMPOSE_PROJECT_NAME=traefik docker compose up -d
cd "$CLAWSUM_DIR"
python3 scripts/patch-control-ui-origins.py 2>/dev/null || true
python3 scripts/patch-control-ui-trusted-proxy.py 2>/dev/null || true
docker compose restart openclaw-gateway 2>/dev/null || true
bash scripts/hermes-dashboard.sh start 2>/dev/null || true

echo ""
echo "=== clawsum.com hosts configured ==="
echo "Funnel:    https://${DOMAIN}  https://${WWW_HOST}"
echo "Login:     https://${LOGIN_HOST}"
echo "Connect:   https://${CONNECT_HOST}"
echo "Hermes:    https://${HERMES_HOST}"
echo "Boss:      https://${BOSS_HOST}"
echo "OpenClaw:  https://${OPENCLAW_HOST}"
echo "Grafana:   https://${GRAFANA_HOST}"
echo "Auth user: ${AUTH_USER}"
echo "Marketing: ${MARKETING_URL}"
echo "DNS A records must point at this VPS before certs issue."
