#!/usr/bin/env bash
# Cut over domains:
#   boss.clawsum.com      → Hermes CEO UI (was hermes.clawsum.com)
#   paperclip.clawsum.com → Paperclip Boss UI (was boss.clawsum.com)
#   hermes.clawsum.com    → 308 redirect → boss.clawsum.com
# Authelia forwardAuth stays on all ops hosts (*.clawsum.com).
set -euo pipefail

TRAEFIK_DIR="${TRAEFIK_DIR:-/docker/traefik}"
CLAWSUM_DIR="${CLAWSUM_DIR:-/docker/clawsum}"
ENV_FILE="${CLAWSUM_DIR}/.env"
DOMAIN="${CLAWSUM_DOMAIN:-clawsum.com}"
HERMES_PORT="${HERMES_DASHBOARD_PORT:-9119}"
OPENCLAW_PORT="${OPENCLAW_GATEWAY_PORT:-48166}"
MARKETING_PORT="${MARKETING_PORT:-8088}"

BOSS_HOST="boss.${DOMAIN}"           # Hermes / CEO cockpit
PAPERCLIP_HOST="paperclip.${DOMAIN}" # Paperclip tasks
HERMES_LEGACY="hermes.${DOMAIN}"     # redirect → boss
OPENCLAW_HOST="openclaw.${DOMAIN}"
GRAFANA_HOST="grafana.${DOMAIN}"
ARCADE_HOST="arcade.${DOMAIN}"
LOGIN_HOST="login.${DOMAIN}"
CONNECT_HOST="connect.${DOMAIN}"
WWW_HOST="www.${DOMAIN}"
AUTH_HOST="auth.${DOMAIN}"

echo "== writing Traefik ${TRAEFIK_DIR}/dynamic/clawsum-com.yml =="
mkdir -p "${TRAEFIK_DIR}/dynamic"
cat > "${TRAEFIK_DIR}/dynamic/clawsum-com.yml" <<EOF
http:
  middlewares:
    clawsum-ops-auth:
      # Authelia SSO — session cookie on .${DOMAIN}
      forwardAuth:
        address: http://127.0.0.1:9091/api/authz/forward-auth
        trustForwardHeader: true
        authResponseHeaders:
          - Remote-User
          - Remote-Groups
          - Remote-Name
          - Remote-Email
    clawsum-ops-user-header:
      headers:
        customRequestHeaders:
          X-Forwarded-User: "boss"
        customResponseHeaders:
          X-Clawsum-Auth: "authelia"
    hermes-host-rewrite:
      headers:
        customRequestHeaders:
          # Loopback Host/Origin so Hermes Host-guard + WS accept Traefik traffic
          Host: "127.0.0.1:${HERMES_PORT}"
          Origin: "http://127.0.0.1:${HERMES_PORT}"
    hermes-to-boss-redirect:
      redirectRegex:
        regex: "^https?://[^/]+(.*)"
        replacement: "https://${BOSS_HOST}\${1}"
        permanent: true

  routers:
    clawsum-authelia:
      rule: Host(\`${AUTH_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-authelia
      tls:
        certResolver: letsencrypt
      priority: 100

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
        - clawsum-ops-user-header
      tls:
        certResolver: letsencrypt

    clawsum-connect:
      rule: Host(\`${CONNECT_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-marketing
      middlewares:
        - clawsum-ops-auth
        - clawsum-ops-user-header
      tls:
        certResolver: letsencrypt

    # Primary CEO face — Hermes dashboard
    clawsum-boss:
      rule: Host(\`${BOSS_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-hermes
      middlewares:
        - clawsum-ops-auth
        - clawsum-ops-user-header
        - hermes-host-rewrite
      tls:
        certResolver: letsencrypt

    # Paperclip task / approval UI
    clawsum-paperclip:
      rule: Host(\`${PAPERCLIP_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-paperclip
      middlewares:
        - clawsum-ops-auth
        - clawsum-ops-user-header
      tls:
        certResolver: letsencrypt

    # Legacy Hermes hostname → boss
    clawsum-hermes-legacy:
      rule: Host(\`${HERMES_LEGACY}\`)
      entryPoints:
        - websecure
      service: clawsum-hermes
      middlewares:
        - hermes-to-boss-redirect
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
        - clawsum-ops-user-header
      tls:
        certResolver: letsencrypt

    clawsum-arcade:
      rule: Host(\`${ARCADE_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-arcade
      middlewares:
        - clawsum-ops-auth
        - clawsum-ops-user-header
      tls:
        certResolver: letsencrypt

  services:
    clawsum-authelia:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:9091
    clawsum-marketing:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:${MARKETING_PORT}
    clawsum-hermes:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:${HERMES_PORT}
    clawsum-paperclip:
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
    clawsum-arcade:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:2480
EOF

echo "== updating ${ENV_FILE} =="
touch "$ENV_FILE"
set_kv() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >>"$ENV_FILE"
  fi
}
set_kv TRAEFIK_HOST "$DOMAIN"
set_kv BOSS_UI_HOST "$BOSS_HOST"
set_kv PAPERCLIP_UI_HOST "$PAPERCLIP_HOST"
set_kv HERMES_UI_HOST "$BOSS_HOST"
set_kv OPENCLAW_UI_HOST "$OPENCLAW_HOST"
set_kv GRAFANA_UI_HOST "$GRAFANA_HOST"
set_kv ARCADE_UI_HOST "$ARCADE_HOST"
set_kv CLAWSUM_ARCADE_URL "https://${ARCADE_HOST}"
set_kv LOGIN_UI_HOST "$LOGIN_HOST"
set_kv CONNECT_UI_HOST "$CONNECT_HOST"
set_kv PAPERCLIP_PUBLIC_URL "https://${PAPERCLIP_HOST}"
set_kv CLAWSUM_BOSS_URL "https://${PAPERCLIP_HOST}"
set_kv CLAWSUM_HERMES_URL "https://${BOSS_HOST}"
set_kv CLAWSUM_OPENCLAW_URL "https://${OPENCLAW_HOST}"
set_kv CLAWSUM_GRAFANA_URL "https://${GRAFANA_HOST}"
set_kv CLAWSUM_AUTH authelia

echo "== Authelia default redirect → boss =="
AUTHELIA_CFG="/docker/authelia/config/configuration.yml"
if [[ -f "$AUTHELIA_CFG" ]]; then
  python3 - <<PY
from pathlib import Path
p = Path("${AUTHELIA_CFG}")
t = p.read_text()
old = "default_redirection_url: 'https://login.${DOMAIN}'"
new = "default_redirection_url: 'https://${BOSS_HOST}'"
if old in t:
    p.write_text(t.replace(old, new, 1))
    print("updated default_redirection_url")
elif "default_redirection_url:" in t:
    import re
    t2 = re.sub(
        r"default_redirection_url:\s*'[^']*'",
        "default_redirection_url: 'https://${BOSS_HOST}'",
        t,
        count=1,
    )
    p.write_text(t2)
    print("updated default_redirection_url (regex)")
else:
    print("no default_redirection_url found")
PY
  cd /docker/authelia && docker compose up -d --force-recreate 2>/dev/null \
    || docker compose -f /docker/authelia/docker-compose.yml up -d --force-recreate
fi

echo "== refresh marketing login/connect pages =="
SITE_DST="${CLAWSUM_DIR}/data/sites/clawsum-com"
SITE_SRC="${CLAWSUM_DIR}/sites/clawsum-com"
[[ -d "$SITE_SRC" ]] || SITE_SRC="${CLAWSUM_DIR}/deploy/sites/clawsum-com"
if [[ -d "$SITE_SRC" ]]; then
  mkdir -p "$SITE_DST"
  cp -a "${SITE_SRC}/." "$SITE_DST/"
  echo "copied site from $SITE_SRC"
fi

echo "== refresh clawsum-runtime.env for Hermes plugins =="
if [[ -f "${CLAWSUM_DIR}/deploy/scripts/fix-clawsum-sidebar-ui.sh" ]]; then
  # Only rewrite env keys — avoid full plugin rebuild here
  python3 - <<PY
from pathlib import Path
env = {}
for line in Path("${ENV_FILE}").read_text(encoding="utf-8", errors="replace").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")
keys = [
    "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
    "GMAIL_ADMIN_ADDRESS", "CLAWSUM_BOSS_URL", "CLAWSUM_OPENCLAW_URL", "CLAWSUM_GRAFANA_URL",
    "CLAWSUM_GRAFANA_EMBED_URL", "CLAWSUM_HERMES_URL", "CLAWSUM_ARCADE_URL",
    "PAPERCLIP_API", "PAPERCLIP_COMPANY_ID",
]
lines = ["# generated for Hermes cockpit plugins — do not commit"]
for k in keys:
    if k == "POSTGRES_HOST":
        lines.append(f"{k}={env.get(k) or '127.0.0.1'}")
    elif k == "POSTGRES_PORT":
        lines.append(f"{k}={env.get(k) or '5432'}")
    elif env.get(k):
        lines.append(f"{k}={env[k]}")
out = Path("${CLAWSUM_DIR}/paperclip-data/.hermes/clawsum-runtime.env")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", out)
PY
  docker cp "${CLAWSUM_DIR}/paperclip-data/.hermes/clawsum-runtime.env" \
    clawsum-paperclip-1:/paperclip/.hermes/clawsum-runtime.env 2>/dev/null || true
  docker cp "${CLAWSUM_DIR}/paperclip-data/.hermes/clawsum-runtime.env" \
    clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/clawsum-runtime.env 2>/dev/null || true
fi

echo "== restart Paperclip with new public URL =="
cd "$CLAWSUM_DIR"
docker compose --profile orchestration up -d paperclip 2>/dev/null \
  || docker compose up -d paperclip 2>/dev/null || true

echo "== patch OpenClaw origins + restart gateway =="
python3 "${CLAWSUM_DIR}/scripts/patch-control-ui-origins.py" 2>/dev/null \
  || python3 "${CLAWSUM_DIR}/deploy/scripts/patch-control-ui-origins.py" 2>/dev/null || true
docker compose restart openclaw-gateway 2>/dev/null || true

echo "== restart Hermes dashboard (pick up runtime env) =="
bash "${CLAWSUM_DIR}/scripts/hermes-dashboard.sh" stop || true
sleep 1
bash "${CLAWSUM_DIR}/scripts/hermes-dashboard.sh" start || true

echo "== wait for Traefik cert / routes =="
sleep 5

echo "== smoke =="
for host in "$BOSS_HOST" "$PAPERCLIP_HOST" "$OPENCLAW_HOST" "$GRAFANA_HOST" "$ARCADE_HOST" "$LOGIN_HOST" "$AUTH_HOST"; do
  code=$(curl -sS -o /dev/null -w '%{http_code}' --resolve "${host}:443:127.0.0.1" "https://${host}/" -k || echo err)
  echo "  ${host} → ${code}"
done
# legacy redirect
code=$(curl -sS -o /dev/null -w '%{http_code}' --resolve "${HERMES_LEGACY}:443:127.0.0.1" "https://${HERMES_LEGACY}/" -k || echo err)
loc=$(curl -sS -o /dev/null -w '%{redirect_url}' --resolve "${HERMES_LEGACY}:443:127.0.0.1" "https://${HERMES_LEGACY}/" -k || true)
echo "  ${HERMES_LEGACY} → ${code} redirect=${loc}"

echo
echo "=== cutover done ==="
echo "Boss (Hermes):   https://${BOSS_HOST}"
echo "Paperclip:       https://${PAPERCLIP_HOST}"
echo "Legacy Hermes:   https://${HERMES_LEGACY} → ${BOSS_HOST}"
echo "SSO:             https://${AUTH_HOST} (Authelia on all ops *.${DOMAIN})"
echo "Arcade Studio:   https://${ARCADE_HOST}"
echo "Login launcher:  https://${LOGIN_HOST}"
