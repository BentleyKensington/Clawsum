#!/usr/bin/env bash
# Deploy Authelia SSO for Clawsum ops hosts (cookie on .clawsum.com).
# Replaces Traefik basicAuth with forwardAuth so browsers stay logged in.
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
ENV_FILE="${ROOT}/.env"
AUTH_DIR="${AUTHELIA_DIR:-/docker/authelia}"
TRAEFIK_YML="${TRAEFIK_YML:-/docker/traefik/dynamic/clawsum-com.yml}"
DOMAIN="${CLAWSUM_DOMAIN:-clawsum.com}"
AUTH_HOST="auth.${DOMAIN}"
TEMPLATE="${ROOT}/authelia/configuration.template.yml"
# Flat VPS may also have examples under /docker/clawsum/authelia after sync
if [[ ! -f "$TEMPLATE" && -f "${ROOT}/deploy/authelia/configuration.template.yml" ]]; then
  TEMPLATE="${ROOT}/deploy/authelia/configuration.template.yml"
fi

USER=$(grep -E '^BOSS_OPS_AUTH_USER=' "$ENV_FILE" | cut -d= -f2- | tr -d '\r')
PASS=$(grep -E '^BOSS_OPS_AUTH_PASSWORD=' "$ENV_FILE" | cut -d= -f2- | tr -d '\r')
: "${USER:?missing BOSS_OPS_AUTH_USER}"
: "${PASS:?missing BOSS_OPS_AUTH_PASSWORD}"

mkdir -p "${AUTH_DIR}/config"
if [[ -f "${ROOT}/authelia/docker-compose.yml" ]]; then
  cp -f "${ROOT}/authelia/docker-compose.yml" "${AUTH_DIR}/docker-compose.yml"
elif [[ -f "${ROOT}/deploy/authelia/docker-compose.yml" ]]; then
  cp -f "${ROOT}/deploy/authelia/docker-compose.yml" "${AUTH_DIR}/docker-compose.yml"
fi

echo "== secrets =="
SECRETS="${AUTH_DIR}/config/.secrets.env"
if [[ ! -f "$SECRETS" ]]; then
  python3 - <<PY
import secrets
from pathlib import Path
p = Path("${SECRETS}")
lines = [
  f"JWT_SECRET={secrets.token_hex(32)}",
  f"SESSION_SECRET={secrets.token_hex(32)}",
  f"STORAGE_KEY={secrets.token_urlsafe(48)}",
]
p.write_text("\n".join(lines) + "\n")
print("wrote", p)
PY
fi
# shellcheck disable=SC1090
set -a; source "$SECRETS"; set +a
: "${JWT_SECRET:?}"; : "${SESSION_SECRET:?}"; : "${STORAGE_KEY:?}"

echo "== configuration.yml =="
python3 - <<PY
from pathlib import Path
tpl = Path("${TEMPLATE}").read_text()
out = (tpl
  .replace("{{JWT_SECRET}}", """${JWT_SECRET}""")
  .replace("{{SESSION_SECRET}}", """${SESSION_SECRET}""")
  .replace("{{STORAGE_KEY}}", """${STORAGE_KEY}""")
)
Path("${AUTH_DIR}/config/configuration.yml").write_text(out)
print("wrote configuration.yml")
PY

echo "== hash password + users_database.yml =="
# Prefer hashing inside Authelia image (argon2 compatible)
HASH=$(docker run --rm authelia/authelia:4.39.6 authelia crypto hash generate argon2 --password "${PASS}" | awk '/Digest:/{print $2; exit}')
if [[ -z "$HASH" ]]; then
  echo "ERROR: failed to hash password with Authelia image" >&2
  exit 1
fi
# YAML single-quoted: escape embedded single quotes
HASH_ESC=${HASH//\'/\'\'}
EMAIL=$(grep -E '^GMAIL_ADMIN_ADDRESS=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '\r' || true)
EMAIL="${EMAIL:-clawsums@gmail.com}"
cat > "${AUTH_DIR}/config/users_database.yml" <<EOF
users:
  ${USER}:
    displayname: "Boss"
    password: '${HASH_ESC}'
    email: ${EMAIL}
    groups:
      - admins
EOF
chmod 600 "${AUTH_DIR}/config/users_database.yml" "${AUTH_DIR}/config/configuration.yml" "$SECRETS"
echo "user=${USER} email=${EMAIL}"

echo "== start Authelia =="
cd "$AUTH_DIR"
docker compose pull
docker compose up -d
sleep 3
if ! curl -sf http://127.0.0.1:9091/api/health >/dev/null 2>&1; then
  # older health path
  curl -sf http://127.0.0.1:9091/ >/dev/null 2>&1 || true
  docker compose logs --tail 40
fi
curl -sS -o /tmp/authelia-health.txt -w "authelia_http:%{http_code}\n" http://127.0.0.1:9091/api/health || true
head -c 200 /tmp/authelia-health.txt; echo

echo "== Traefik: forwardAuth + auth host =="
python3 - <<'PY'
from pathlib import Path
p = Path("/docker/traefik/dynamic/clawsum-com.yml")
t = p.read_text()

# Middleware block
old_mw = """    clawsum-ops-auth:
      basicAuth:
        usersFile: /dynamic/clawsum-ops.htpasswd
"""
new_mw = """    clawsum-ops-auth:
      # Authelia SSO — session cookie on .clawsum.com (no basic-auth re-prompt)
      forwardAuth:
        address: http://127.0.0.1:9091/api/authz/forward-auth
        trustForwardHeader: true
        authResponseHeaders:
          - Remote-User
          - Remote-Groups
          - Remote-Name
          - Remote-Email
"""
if "api/authz/forward-auth" in t:
    print("forwardAuth already present")
elif old_mw in t:
    t = t.replace(old_mw, new_mw, 1)
    print("replaced basicAuth with forwardAuth")
else:
    raise SystemExit("clawsum-ops-auth basicAuth block not found")

# Prefer Remote-User from Authelia for apps; keep boss fallback header for Grafana
user_hdr = """    clawsum-ops-user-header:
      headers:
        customRequestHeaders:
          X-Forwarded-User: \"boss\"
"""
user_hdr_new = """    clawsum-ops-user-header:
      headers:
        customRequestHeaders:
          # Fallback when Remote-User not forwarded; Authelia also sets Remote-User
          X-Forwarded-User: \"boss\"
        customResponseHeaders:
          X-Clawsum-Auth: \"authelia\"
"""
if user_hdr in t and "X-Clawsum-Auth" not in t:
    t = t.replace(user_hdr, user_hdr_new, 1)

# Ensure auth.clawsum.com router exists (before services section)
if "clawsum-authelia:" not in t:
    insert_router = """
    clawsum-authelia:
      rule: Host(`auth.clawsum.com`)
      entryPoints:
        - websecure
      service: clawsum-authelia
      tls:
        certResolver: letsencrypt
      priority: 100

"""
    # insert after middlewares / before first marketing router or after clawsum-marketing
    anchor = "    clawsum-marketing:"
    if anchor not in t:
        raise SystemExit("clawsum-marketing router missing")
    t = t.replace(anchor, insert_router + anchor, 1)
    print("added clawsum-authelia router")

if "clawsum-authelia:" not in t.split("services:")[-1]:
    # add service
    svc = """    clawsum-authelia:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:9091
"""
    if "  services:" in t and "clawsum-authelia:" not in t[t.find("  services:"):]:
        # append after services:
        idx = t.find("  services:")
        # find end - insert after services line
        rest = t[idx:]
        nl = rest.find("\n")
        t = t[: idx + nl + 1] + svc + rest[nl + 1 :]
        print("added clawsum-authelia service")

p.write_text(t)
print("wrote", p)
PY

# Traefik file provider watches; bounce if needed
docker restart traefik-traefik-1 >/dev/null 2>&1 || true
sleep 4

echo "== smoke =="
# Unauthenticated ops host should redirect to Authelia (302/303/401)
for host in hermes boss grafana login; do
  code=$(curl -sS -o /tmp/a.out -w '%{http_code}' --max-redirs 0 "https://${host}.${DOMAIN}/" -k || true)
  loc=$(grep -i '^location:' /tmp/a.out 2>/dev/null | head -1 || true)
  # curl -D-
  hdr=$(curl -sS -D- -o /dev/null --max-redirs 0 "https://${host}.${DOMAIN}/" -k 2>/dev/null | tr -d '\r' | head -20)
  echo "--- ${host} ---"
  echo "$hdr" | head -12
done
code=$(curl -sS -o /dev/null -w '%{http_code}' "https://${AUTH_HOST}/" -k || true)
echo "auth portal: ${code}"

# Persist flag in .env
grep -q '^CLAWSUM_AUTH=authelia' "$ENV_FILE" 2>/dev/null \
  || echo 'CLAWSUM_AUTH=authelia' >>"$ENV_FILE"

cat <<EOF

OK — Authelia SSO enabled.

1) Open https://${AUTH_HOST}/  (or any ops host; you will be redirected)
2) Login once: user=${USER}  (same password as before)
3) Cookie domain=.${DOMAIN} — stays logged in across hermes/boss/grafana/login (~14d)

Marketing https://${DOMAIN} stays public (no Authelia).
EOF
