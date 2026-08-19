#!/usr/bin/env bash
# Unify ops portal to ONE login: Traefik basic auth (boss / BOSS_OPS_AUTH_PASSWORD).
set -euo pipefail

ENV_FILE=/docker/clawsum/.env
TRAEFIK_YML=/docker/traefik/dynamic/clawsum-com.yml
COMPOSE=/docker/clawsum/docker-compose.yml

USER=$(grep -E '^BOSS_OPS_AUTH_USER=' "$ENV_FILE" | cut -d= -f2- | tr -d '\r')
PASS=$(grep -E '^BOSS_OPS_AUTH_PASSWORD=' "$ENV_FILE" | cut -d= -f2- | tr -d '\r')
: "${USER:?missing BOSS_OPS_AUTH_USER}"
: "${PASS:?missing BOSS_OPS_AUTH_PASSWORD}"

echo "== sync GRAFANA_ADMIN_PASSWORD to BOSS_OPS password =="
python3 - <<PY
from pathlib import Path
boss = """$PASS"""
user = """$USER"""
path = Path("$ENV_FILE")
lines = path.read_text().splitlines()
out = []
seen = set()
updates = {
    "GRAFANA_ADMIN_PASSWORD": boss,
    "GRAFANA_AUTH_PROXY": "true",
}
for line in lines:
    if "=" in line and not line.strip().startswith("#"):
        k = line.split("=", 1)[0].strip()
        if k in updates:
            out.append(f"{k}={updates[k]}")
            seen.add(k)
            continue
    out.append(line)
for k, v in updates.items():
    if k not in seen:
        out.append(f"{k}={v}")
path.write_text("\n".join(out) + "\n")
print("synced GRAFANA_ADMIN_PASSWORD + GRAFANA_AUTH_PROXY")
PY

echo "== Traefik: X-Forwarded-User on all ops routers =="
python3 - <<'PY'
from pathlib import Path
import re
p = Path("/docker/traefik/dynamic/clawsum-com.yml")
text = p.read_text()
if "clawsum-ops-user-header:" not in text:
    raise SystemExit("missing clawsum-ops-user-header middleware")

def set_mws(name: str, mws: list[str], src: str) -> str:
    block = "".join(f"        - {m}\n" for m in mws)
    pat = re.compile(
        rf"(    {re.escape(name)}:\n(?:.*?\n)*?      middlewares:\n)((?:        - .*\n)+)",
        re.M,
    )
    if pat.search(src):
        return pat.sub(rf"\1{block}", src, count=1)
    pat2 = re.compile(
        rf"(    {re.escape(name)}:\n(?:.*?\n)*?)(      tls:\n)",
        re.M,
    )
    if pat2.search(src):
        return pat2.sub(rf"\1      middlewares:\n{block}\2", src, count=1)
    print(f"WARN: router {name} not found")
    return src

text2 = text
text2 = set_mws("clawsum-login", ["clawsum-ops-auth", "clawsum-ops-user-header"], text2)
text2 = set_mws("clawsum-connect", ["clawsum-ops-auth", "clawsum-ops-user-header"], text2)
text2 = set_mws("clawsum-boss", ["clawsum-ops-auth", "clawsum-ops-user-header"], text2)
text2 = set_mws("clawsum-openclaw", ["clawsum-ops-auth", "clawsum-ops-user-header"], text2)
text2 = set_mws("clawsum-grafana", ["clawsum-ops-auth", "clawsum-ops-user-header"], text2)
text2 = set_mws(
    "clawsum-hermes",
    ["clawsum-ops-auth", "clawsum-ops-user-header", "hermes-host-rewrite"],
    text2,
)
p.write_text(text2)
print("traefik updated")
PY

echo "== compose grafana auth-proxy env =="
if [[ -f "$COMPOSE" ]]; then
  python3 - <<'PY'
from pathlib import Path
p = Path("/docker/clawsum/docker-compose.yml")
t = p.read_text()
if "GF_AUTH_PROXY_ENABLED" in t:
    print("compose already patched")
elif 'GF_USERS_ALLOW_SIGN_UP: "false"' in t:
    t2 = t.replace(
        'GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-admin_change_me}\n      GF_USERS_ALLOW_SIGN_UP: "false"',
        'GF_SECURITY_ADMIN_USER: ${BOSS_OPS_AUTH_USER:-boss}\n'
        '      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-${BOSS_OPS_AUTH_PASSWORD:-admin_change_me}}\n'
        '      GF_USERS_ALLOW_SIGN_UP: "false"\n'
        '      GF_AUTH_ANONYMOUS_ENABLED: "false"\n'
        '      GF_AUTH_DISABLE_LOGIN_FORM: "true"\n'
        '      GF_AUTH_PROXY_ENABLED: "true"\n'
        '      GF_AUTH_PROXY_HEADER_NAME: X-Forwarded-User\n'
        '      GF_AUTH_PROXY_HEADER_PROPERTY: username\n'
        '      GF_AUTH_PROXY_AUTO_SIGN_UP: "true"\n'
        '      GF_USERS_AUTO_ASSIGN_ORG_ROLE: Admin',
        1,
    )
    p.write_text(t2)
    print("compose patched")
else:
    print("WARN: compose shape unexpected — will still set via docker update if needed")
PY
fi

echo "== recreate grafana =="
cd /docker/clawsum
docker compose --profile monitoring up -d grafana
sleep 4

echo "== reset grafana admin password =="
docker exec clawsum-grafana-1 grafana cli admin reset-admin-password "$PASS" \
  || docker exec -u 0 clawsum-grafana-1 grafana cli admin reset-admin-password "$PASS"

echo "== hermes: no inner basic_auth =="
python3 - <<'PY'
from pathlib import Path
import re
p = Path("/docker/clawsum/paperclip-data/.hermes/config.yaml")
text = p.read_text() if p.exists() else "dashboard:\n  theme: clawsum-command\n"
text2 = re.sub(r"\n[ \t]*basic_auth:.*?(?=\n\S|\Z)", "\n", text, flags=re.S)
if "theme:" not in text2:
    text2 = "dashboard:\n  theme: clawsum-command\n"
p.write_text(text2.strip() + "\n")
print(p.read_text())
PY

echo "== smoke =="
curl -sS -o /dev/null -w "grafana health %{http_code}\n" -u "${USER}:${PASS}" https://grafana.clawsum.com/api/health
curl -sS -o /tmp/gf-user.json -w "grafana /api/user %{http_code}\n" -u "${USER}:${PASS}" https://grafana.clawsum.com/api/user || true
python3 - <<'PY'
import json
from pathlib import Path
try:
    d=json.loads(Path('/tmp/gf-user.json').read_text())
    print('grafana user', d.get('login') or d.get('name') or d)
except Exception as e:
    print('grafana user parse', e, Path('/tmp/gf-user.json').read_text()[:200])
PY
curl -sS -o /dev/null -w "hermes root %{http_code}\n" -u "${USER}:${PASS}" https://hermes.clawsum.com/
curl -sS -u "${USER}:${PASS}" https://hermes.clawsum.com/api/status | python3 -c "import sys,json; d=json.load(sys.stdin); print('hermes auth_required=', d.get('auth_required'), 'providers=', d.get('auth_providers'))"
echo "DONE — single Traefik login user=${USER}"
