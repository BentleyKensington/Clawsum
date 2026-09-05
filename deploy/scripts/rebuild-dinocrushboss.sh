#!/usr/bin/env bash
# Rebuild + restart the public Dino Crush game only (no Traefik/DNS).
# Used by dinohawk after editing modules/dinocrushboss (workspace game/).
set -euo pipefail
CLAWSUM_DIR="${CLAWSUM_DIR:-/docker/clawsum}"
MODULE="${CLAWSUM_DIR}/modules/dinocrushboss"
if [[ ! -d "$MODULE" && -d "${CLAWSUM_DIR}/deploy/modules/dinocrushboss" ]]; then
  MODULE="${CLAWSUM_DIR}/deploy/modules/dinocrushboss"
fi
[[ -d "$MODULE" ]] || { echo "ERROR: dinocrushboss module missing" >&2; exit 1; }

GAME_PORT="${DINOCRUSHBOSS_PORT:-8092}"
DOMAIN="${DINOCRUSHBOSS_DOMAIN:-dinocrushboss.com}"
LOGIN_HOST="${DINOCRUSHBOSS_LOGIN_HOST:-login.dinocrushboss.com}"
GAME_HOST="${DINOCRUSHBOSS_GAME_HOST:-game.dinocrushboss.com}"
ENV_FILE="${CLAWSUM_DIR}/.env"
if [[ -f "$ENV_FILE" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" == *"="* ]] || continue
    key="${line%%=*}"
    val="${line#*=}"
    val="${val#\"}"; val="${val%\"}"
    val="${val#\'}"; val="${val%\'}"
    case "$key" in
      POSTGRES_HOST|POSTGRES_PORT|POSTGRES_USER|POSTGRES_PASSWORD|POSTGRES_DB|SESSION_SECRET|DINOCRUSHBOSS_SESSION_SECRET|DINOCRUSHBOSS_EMAIL|DINOCRUSHBOSS_PLAY_EMAIL|DINOCRUSHBOSS_PLAY_PASSWORD)
        export "$key=$val"
        ;;
    esac
  done < "$ENV_FILE"
fi

SESSION_SECRET="${DINOCRUSHBOSS_SESSION_SECRET:-${SESSION_SECRET:-}}"
if [[ -z "$SESSION_SECRET" ]] && docker inspect dinocrushboss >/dev/null 2>&1; then
  SESSION_SECRET="$(docker inspect dinocrushboss --format '{{range .Config.Env}}{{println .}}{{end}}' | awk -F= '/^SESSION_SECRET=/{print $2; exit}')"
fi
if [[ -z "$SESSION_SECRET" ]]; then
  SESSION_SECRET="$(openssl rand -hex 32)"
fi

PG_HOST="${POSTGRES_HOST:-127.0.0.1}"
PG_PORT="${POSTGRES_PORT:-5432}"
PG_USER="${POSTGRES_USER:-clawsum}"
PG_DB="${POSTGRES_DB:-clawsum}"
PG_PASS="${POSTGRES_PASSWORD:-}"
DATABASE_URL="postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/${PG_DB}"

echo "== rebuild dinocrushboss =="
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

ok=0
for _ in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${GAME_PORT}/api/health" >/dev/null; then
    ok=1
    break
  fi
  sleep 2
done
if [[ "$ok" != "1" ]]; then
  echo "ERROR: dinocrushboss not healthy after rebuild" >&2
  docker logs dinocrushboss 2>&1 | tail -30
  exit 1
fi
echo "DINOCRUSHBOSS_REBUILD_OK http://127.0.0.1:${GAME_PORT}/"
