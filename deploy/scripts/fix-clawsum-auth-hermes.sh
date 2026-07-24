#!/bin/bash
# Rewrite Traefik basic-auth user, fix OpenClaw docker Host label, smoke test.
set -euo pipefail
USER=boss
PASS="$(openssl rand -hex 12)"
HT="$(htpasswd -nbB "$USER" "$PASS" | tr -d '\r\n')"
HT_ESC="${HT//\$/\$\$}"

# Update .env auth
python3 - <<PY
from pathlib import Path
env = Path("/docker/clawsum/.env")
lines = [ln for ln in env.read_text().splitlines()
         if not ln.startswith("BOSS_OPS_AUTH_USER=")
         and not ln.startswith("BOSS_OPS_AUTH_PASSWORD=")]
lines += ["BOSS_OPS_AUTH_USER=boss", "BOSS_OPS_AUTH_PASSWORD=${PASS}"]
env.write_text("\\n".join(lines) + "\\n")
print("env auth updated")
PY

# Rewrite users line in clawsum-com.yml
python3 - <<PY
from pathlib import Path
import re
p = Path("/docker/traefik/dynamic/clawsum-com.yml")
t = p.read_text()
ht = "${HT_ESC}"
t = t.replace("boss.srv1669521.hstgr.cloud", "boss.clawsum.com")
t2, n = re.subn(r'(users:\n\s+- ")[^"]+(")', r"\\1" + ht + r"\\2", t, count=1)
if n != 1:
    raise SystemExit(f"failed to rewrite users line (n={n})")
p.write_text(t2)
print("yml auth updated", ht[:32], "...")
PY

echo "$PASS" > /root/.clawsum-ops-pass
chmod 600 /root/.clawsum-ops-pass

# Fix OpenClaw compose label Host(clawsum.${TRAEFIK_HOST}) -> openclaw.clawsum.com
# Prefer disabling confusing label; Traefik file provider already routes openclaw.clawsum.com
if grep -q 'traefik.http.routers.clawsum.rule' /docker/clawsum/docker-compose.yml; then
  sed -i 's|traefik.http.routers.clawsum.rule=Host(`clawsum.\${TRAEFIK_HOST:-localhost}`)|traefik.http.routers.clawsum.rule=Host(`openclaw.clawsum.com`)|' /docker/clawsum/docker-compose.yml || true
fi

cd /docker/clawsum
docker compose up -d openclaw-gateway 2>/dev/null || true

# Restart Traefik to force file reload
cd /docker/traefik
env -u COMPOSE_PROJECT_NAME COMPOSE_PROJECT_NAME=traefik docker compose up -d --force-recreate 2>/dev/null || docker restart traefik-traefik-1
sleep 3

# Hermes
docker exec -u root clawsum-paperclip-1 bash -lc '
  pkill -f "hermes dashboard" 2>/dev/null || true
  H=/paperclip/.hermes-venv/bin/hermes
  [[ -x $H ]] || H=/usr/local/bin/hermes
  mkdir -p /paperclip/logs
  nohup "$H" dashboard --host 127.0.0.1 --port 9119 --no-open >>/paperclip/logs/hermes-dashboard.log 2>&1 &
  sleep 3
  curl -sf http://127.0.0.1:9119/ >/dev/null && echo hermes_local=ok || echo hermes_local=fail
'

PASS="$(cat /root/.clawsum-ops-pass)"
echo "Testing with fresh password (also in /root/.clawsum-ops-pass)"
curl -sS -o /dev/null -w 'apex=%{http_code}\n' --resolve clawsum.com:443:127.0.0.1 https://clawsum.com/ -k
curl -sS -o /dev/null -w 'hermes=%{http_code}\n' --resolve hermes.clawsum.com:443:127.0.0.1 -u "boss:${PASS}" https://hermes.clawsum.com/ -k
curl -sS -o /dev/null -w 'boss=%{http_code}\n' --resolve boss.clawsum.com:443:127.0.0.1 -u "boss:${PASS}" https://boss.clawsum.com/api/health -k
curl -sS -o /dev/null -w 'login=%{http_code}\n' --resolve login.clawsum.com:443:127.0.0.1 -u "boss:${PASS}" https://login.clawsum.com/ -k
curl -sS -o /dev/null -w 'grafana=%{http_code}\n' --resolve grafana.clawsum.com:443:127.0.0.1 -u "boss:${PASS}" https://grafana.clawsum.com/ -k
