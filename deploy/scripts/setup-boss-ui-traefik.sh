#!/bin/bash
# Add Traefik file provider + Boss UI route to Paperclip (127.0.0.1:3100).
set -euo pipefail

TRAEFIK_DIR="${TRAEFIK_DIR:-/docker/traefik}"
CLAWSUM_DIR="${CLAWSUM_DIR:-/docker/clawsum}"
BOSS_HOST="${BOSS_HOST:-boss.srv.example.com}"

mkdir -p "${TRAEFIK_DIR}/dynamic"

cat > "${TRAEFIK_DIR}/dynamic/boss-ui.yml" <<EOF
http:
  routers:
    clawsum-boss:
      rule: Host(\`${BOSS_HOST}\`)
      entryPoints:
        - websecure
      service: clawsum-boss
      tls:
        certResolver: letsencrypt
  services:
    clawsum-boss:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:3100
EOF

COMPOSE="${TRAEFIK_DIR}/docker-compose.yml"
if ! grep -q 'providers.file.directory' "$COMPOSE"; then
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
  export COMPOSE
fi

# Clawsum .env — public URL for Better Auth
ENV_FILE="${CLAWSUM_DIR}/.env"
if grep -q '^PAPERCLIP_PUBLIC_URL=' "$ENV_FILE" 2>/dev/null; then
  sed -i "s|^PAPERCLIP_PUBLIC_URL=.*|PAPERCLIP_PUBLIC_URL=https://${BOSS_HOST}|" "$ENV_FILE"
else
  echo "PAPERCLIP_PUBLIC_URL=https://${BOSS_HOST}" >> "$ENV_FILE"
fi
grep -q '^BOSS_UI_HOST=' "$ENV_FILE" 2>/dev/null || echo "BOSS_UI_HOST=${BOSS_HOST}" >> "$ENV_FILE"

cd "$TRAEFIK_DIR"
docker compose up -d
cd "$CLAWSUM_DIR"
docker compose --profile orchestration up -d paperclip

echo ""
echo "Boss UI route: https://${BOSS_HOST}"
echo "DNS: A or CNAME ${BOSS_HOST} -> VPS IP"
echo "Test: curl -sS -o /dev/null -w '%{http_code}\n' https://${BOSS_HOST}/api/health"
