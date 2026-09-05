#!/usr/bin/env bash
# Publish dinocrushboss.com (promo) + login/game hosts + Traefik.
# Kid lane — no Authelia, no cash. DNS/TLS = Tier 2.
set -euo pipefail
CLAWSUM_DIR="${CLAWSUM_DIR:-/docker/clawsum}"
TRAEFIK_DIR="${TRAEFIK_DIR:-/docker/traefik}"
AUTH_DIR="${AUTHELIA_DIR:-/docker/authelia}"
DOMAIN="${DINOCRUSHBOSS_DOMAIN:-dinocrushboss.com}"
WWW_HOST="${DINOCRUSHBOSS_WWW_HOST:-www.dinocrushboss.com}"
LOGIN_HOST="${DINOCRUSHBOSS_LOGIN_HOST:-login.dinocrushboss.com}"
GAME_HOST="${DINOCRUSHBOSS_GAME_HOST:-game.dinocrushboss.com}"
GAME_PORT="${DINOCRUSHBOSS_PORT:-8092}"
PROMO_PORT="${DINOCRUSHBOSS_PROMO_PORT:-8095}"
MODULE="${CLAWSUM_DIR}/modules/dinocrushboss"
SITE_SRC="${CLAWSUM_DIR}/sites/dinocrushboss-com"
SITE_DST="${CLAWSUM_DIR}/data/sites/dinocrushboss-com"

if [[ ! -d "$MODULE" && -d "${CLAWSUM_DIR}/deploy/modules/dinocrushboss" ]]; then
  MODULE="${CLAWSUM_DIR}/deploy/modules/dinocrushboss"
fi
if [[ ! -d "$MODULE" ]]; then
  echo "ERROR: modules/dinocrushboss not found" >&2
  exit 1
fi
if [[ ! -d "$SITE_SRC" && -d "${CLAWSUM_DIR}/deploy/sites/dinocrushboss-com" ]]; then
  SITE_SRC="${CLAWSUM_DIR}/deploy/sites/dinocrushboss-com"
fi
if [[ ! -d "$SITE_SRC" ]]; then
  echo "ERROR: sites/dinocrushboss-com not found" >&2
  exit 1
fi

echo "== schema =="
for _ in $(seq 1 30); do
  docker exec clawsum-postgres-1 pg_isready -U "${POSTGRES_USER:-clawsum}" >/dev/null 2>&1 && break
  sleep 2
done
ENV_FILE="${CLAWSUM_DIR}/.env"
if [[ -f "$ENV_FILE" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" == *"="* ]] || continue
    key="${line%%=*}"
    val="${line#*=}"
    key="${key%"${key##*[![:space:]]}"}"
    val="${val#\"}"; val="${val%\"}"
    val="${val#\'}"; val="${val%\'}"
    case "$key" in
      POSTGRES_HOST|POSTGRES_PORT|POSTGRES_USER|POSTGRES_PASSWORD|POSTGRES_DB|SESSION_SECRET|DINOCRUSHBOSS_SESSION_SECRET|DINOCRUSHBOSS_EMAIL|DINOCRUSHBOSS_PLAY_EMAIL|DINOCRUSHBOSS_PLAY_PASSWORD)
        export "$key=$val"
        ;;
    esac
  done < "$ENV_FILE"
fi
apply_sql() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  docker cp "$f" clawsum-postgres-1:/tmp/dinocrush-apply.sql
  docker exec clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" \
    -v ON_ERROR_STOP=1 -f /tmp/dinocrush-apply.sql \
    || echo "WARN: apply $(basename "$f") manually"
}
SQL26="${CLAWSUM_DIR}/postgres-init/26-ops-dinocrush.sql"
[[ -f "$SQL26" ]] || SQL26="${CLAWSUM_DIR}/deploy/postgres-init/26-ops-dinocrush.sql"
SQL29="${CLAWSUM_DIR}/postgres-init/29-ops-dinocrushboss.sql"
[[ -f "$SQL29" ]] || SQL29="${CLAWSUM_DIR}/deploy/postgres-init/29-ops-dinocrushboss.sql"
SQL30="${CLAWSUM_DIR}/postgres-init/30-ops-dinocrushboss-login.sql"
[[ -f "$SQL30" ]] || SQL30="${CLAWSUM_DIR}/deploy/postgres-init/30-ops-dinocrushboss-login.sql"
apply_sql "$SQL26"
apply_sql "$SQL29"
apply_sql "$SQL30"

echo "== promo nginx :${PROMO_PORT} =="
mkdir -p "$SITE_DST"
cp -a "$SITE_SRC/." "$SITE_DST/"
docker rm -f dinocrushboss-promo 2>/dev/null || true
docker run -d --name dinocrushboss-promo --restart unless-stopped \
  -p "127.0.0.1:${PROMO_PORT}:8080" \
  -v "${SITE_DST}:/usr/share/nginx/html:ro" \
  -v "${SITE_DST}/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:1.27-alpine
sleep 1
curl -sf "http://127.0.0.1:${PROMO_PORT}/" >/dev/null || {
  echo "ERROR: dinocrushboss promo nginx not responding on :${PROMO_PORT}" >&2
  docker logs dinocrushboss-promo 2>&1 | tail -20
  exit 1
}

echo "== game image =="
SESSION_SECRET="${DINOCRUSHBOSS_SESSION_SECRET:-${SESSION_SECRET:-}}"
if [[ -z "$SESSION_SECRET" ]]; then
  SESSION_SECRET="$(openssl rand -hex 32)"
  echo "generated DINOCRUSHBOSS_SESSION_SECRET"
  if [[ -f "$ENV_FILE" ]] && ! grep -q '^DINOCRUSHBOSS_SESSION_SECRET=' "$ENV_FILE"; then
    printf '\nDINOCRUSHBOSS_SESSION_SECRET=%s\n' "$SESSION_SECRET" >> "$ENV_FILE"
    echo "wrote DINOCRUSHBOSS_SESSION_SECRET to .env"
  fi
fi
PG_HOST="${POSTGRES_HOST:-127.0.0.1}"
PG_PORT="${POSTGRES_PORT:-5432}"
PG_USER="${POSTGRES_USER:-clawsum}"
PG_DB="${POSTGRES_DB:-clawsum}"
PG_PASS="${POSTGRES_PASSWORD:-}"
DATABASE_URL="postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/${PG_DB}"

docker build -t clawsum-dinocrushboss:local "$MODULE"

docker rm -f dinocrushboss 2>/dev/null || true
docker run -d --name dinocrushboss --restart unless-stopped --network host \
  -e NODE_ENV=production \
  -e PORT="${GAME_PORT}" \
  -e HOST=127.0.0.1 \
  -e DATABASE_URL="${DATABASE_URL}" \
  -e POSTGRES_HOST="${PG_HOST}" \
  -e POSTGRES_PORT="${PG_PORT}" \
  -e POSTGRES_USER="${PG_USER}" \
  -e POSTGRES_PASSWORD="${PG_PASS}" \
  -e POSTGRES_DB="${PG_DB}" \
  -e SESSION_SECRET="${SESSION_SECRET}" \
  -e COOKIE_SECURE=1 \
  -e COOKIE_DOMAIN=".dinocrushboss.com" \
  -e PUBLIC_LOGIN_URL="https://${LOGIN_HOST}" \
  -e PUBLIC_GAME_URL="https://${GAME_HOST}" \
  -e PUBLIC_PROMO_URL="https://${DOMAIN}" \
  -e DINOCRUSHBOSS_EMAIL="${DINOCRUSHBOSS_EMAIL:-dinocrushboss@gmail.com}" \
  -e DINOCRUSHBOSS_PLAY_EMAIL="${DINOCRUSHBOSS_PLAY_EMAIL:-play@dinocrushboss.com}" \
  -e DINOCRUSHBOSS_PLAY_PASSWORD="${DINOCRUSHBOSS_PLAY_PASSWORD:-DinoCrush}" \
  -e GAME_VERSION="${GAME_VERSION:-1.0.0}" \
  clawsum-dinocrushboss:local

echo "waiting for game health on :${GAME_PORT}"
ok=0
for _ in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${GAME_PORT}/api/health" >/dev/null; then
    ok=1
    break
  fi
  sleep 2
done
if [[ "$ok" != "1" ]]; then
  echo "ERROR: dinocrushboss not healthy" >&2
  docker logs dinocrushboss 2>&1 | tail -40
  exit 1
fi

echo "== Traefik =="
mkdir -p "${TRAEFIK_DIR}/dynamic"
cat > "${TRAEFIK_DIR}/dynamic/dinocrushboss.yml" <<EOF
http:
  routers:
    dinocrushboss-promo:
      rule: Host(\`${DOMAIN}\`) || Host(\`${WWW_HOST}\`)
      entryPoints:
        - websecure
      service: dinocrushboss-promo
      tls:
        certResolver: letsencrypt
      priority: 10
    dinocrushboss-login:
      rule: Host(\`${LOGIN_HOST}\`)
      entryPoints:
        - websecure
      service: dinocrushboss-game
      tls:
        certResolver: letsencrypt
      priority: 20
    dinocrushboss-game:
      rule: Host(\`${GAME_HOST}\`)
      entryPoints:
        - websecure
      service: dinocrushboss-game
      tls:
        certResolver: letsencrypt
      priority: 20
  services:
    dinocrushboss-promo:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:${PROMO_PORT}"
    dinocrushboss-game:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:${GAME_PORT}"
EOF

echo "== Authelia public bypass =="
python3 "${CLAWSUM_DIR}/scripts/authelia_dinohawk_access.py" 2>/dev/null || \
  python3 "${CLAWSUM_DIR}/deploy/scripts/authelia_dinohawk_access.py" || true
cd "$AUTH_DIR"
docker compose restart authelia 2>/dev/null || docker restart clawsum-authelia 2>/dev/null || true

LOGIN_FILE="${CLAWSUM_DIR}/data/dinocrushboss-login.txt"
mkdir -p "$(dirname "$LOGIN_FILE")"
umask 077
cat > "$LOGIN_FILE" <<EOF
PROMO=https://${DOMAIN}
LOGIN=https://${LOGIN_HOST}
GAME=https://${GAME_HOST}
EMAIL=dinocrushboss@gmail.com
EMAIL_EASY=play@dinocrushboss.com
EMAIL_ALIAS=dincrushboss@gmail.com
PASSWORD=${DINOCRUSHBOSS_PLAY_PASSWORD:-DinoCrush}
EOF
chmod 600 "$LOGIN_FILE" || true

echo "== dinohawk game apply watcher =="
WATCH="${CLAWSUM_DIR}/scripts/start-dinocrushboss-apply-watcher.sh"
[[ -f "$WATCH" ]] || WATCH="${CLAWSUM_DIR}/deploy/scripts/start-dinocrushboss-apply-watcher.sh"
bash "$WATCH" || echo "WARN: apply watcher not started"

echo "DINOCRUSHBOSS_OK promo :${PROMO_PORT}  game :${GAME_PORT}"
echo "https://${DOMAIN}/  https://${LOGIN_HOST}/  https://${GAME_HOST}/"
echo "Login file (host only, not git): ${LOGIN_FILE}"
