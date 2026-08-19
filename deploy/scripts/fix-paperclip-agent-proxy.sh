#!/usr/bin/env bash
# Restore Paperclip (local_trusted requires loopback) and expose agent API via proxy :3102
set -euo pipefail
ROOT=/docker/clawsum
cd "$ROOT"

echo "=== Restore Paperclip HOST=127.0.0.1 ==="
python3 - <<'PY'
from pathlib import Path
p = Path("/docker/clawsum/docker-compose.yml")
text = p.read_text()
# only paperclip service HOST line
idx = text.find("  paperclip:")
if idx < 0:
    raise SystemExit("no paperclip")
# replace first HOST after paperclip that is 0.0.0.0
chunk = text[idx:]
old = 'HOST: "0.0.0.0"  # reachable from openclaw-gateway via host.docker.internal'
old2 = 'HOST: "0.0.0.0"'
if old in chunk:
    text = text[:idx] + chunk.replace(old, 'HOST: "127.0.0.1"', 1)
elif 'HOST: "0.0.0.0"' in chunk[:1200]:
    # replace first occurrence in paperclip block only
    pos = chunk.find('HOST: "0.0.0.0"')
    text = text[:idx] + chunk[:pos] + 'HOST: "127.0.0.1"' + chunk[pos+len('HOST: "0.0.0.0"'):]
else:
    print("HOST already loopback or unexpected")
p.write_text(text)
print("compose HOST set to 127.0.0.1 for paperclip")
PY

# Keep gateway env pointing at proxy port 3102
sed -i 's|host.docker.internal:3100/api|host.docker.internal:3102/api|g' "$ROOT/docker-compose.yml" || true
if grep -q '^PAPERCLIP_AGENT_API_URL=' "$ROOT/.env"; then
  sed -i 's|^PAPERCLIP_AGENT_API_URL=.*|PAPERCLIP_AGENT_API_URL=http://host.docker.internal:3102/api|' "$ROOT/.env"
else
  echo 'PAPERCLIP_AGENT_API_URL=http://host.docker.internal:3102/api' >> "$ROOT/.env"
fi

echo "=== Recreate paperclip on loopback ==="
docker compose --profile orchestration up -d --force-recreate paperclip
for i in $(seq 1 30); do
  if curl -sS -m 2 -o /dev/null -w '' http://127.0.0.1:3100/api/health; then
    echo "paperclip healthy after ${i}s"
    break
  fi
  sleep 2
done
curl -sS -m 5 http://127.0.0.1:3100/api/health | head -c 200; echo

echo "=== Install/start agent API proxy :3102 -> 127.0.0.1:3100 ==="
# Prefer socat; fallback to python
if ! command -v socat >/dev/null 2>&1; then
  apt-get update -qq && apt-get install -y -qq socat >/dev/null
fi
systemctl stop clawsum-paperclip-agent-proxy 2>/dev/null || true
pkill -f 'socat TCP-LISTEN:3102' 2>/dev/null || true
cat >/etc/systemd/system/clawsum-paperclip-agent-proxy.service <<'UNIT'
[Unit]
Description=Clawsum Paperclip agent API proxy (3102 -> 127.0.0.1:3100)
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/socat TCP-LISTEN:3102,fork,reuseaddr,bind=0.0.0.0 TCP:127.0.0.1:3100
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now clawsum-paperclip-agent-proxy.service
sleep 1
ss -lntp | grep -E ':(3100|3102)\b' || true
curl -sS -m 5 http://127.0.0.1:3102/api/health | head -c 200; echo

echo "=== Recreate gateway with PAPERCLIP_API_URL=:3102 ==="
docker compose up -d --force-recreate openclaw-gateway
# wait healthy
for i in $(seq 1 30); do
  st=$(docker inspect -f '{{.State.Health.Status}}' clawsum-openclaw-gateway-1 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done

echo "=== Verify from gateway ==="
docker exec clawsum-openclaw-gateway-1 sh -c '
  echo PAPERCLIP_API_URL=$PAPERCLIP_API_URL
  curl -sS -m 5 -o /tmp/h -w "health:%{http_code}\n" http://host.docker.internal:3102/api/health || echo health_fail
  head -c 180 /tmp/h; echo
  curl -sS -m 5 -o /tmp/m -w "me:%{http_code}\n" http://host.docker.internal:3102/api/agents/me || echo me_fail
  head -c 180 /tmp/m; echo
'

# Update TOOLS notes to 3102
python3 - <<'PY'
from pathlib import Path
base = Path("/docker/clawsum/data/.openclaw")
for d in list(base.glob("workspace-ghl*")) + [base / "workspace-slack-avenou"]:
    tools = d / "TOOLS.md"
    if not tools.exists():
        continue
    text = tools.read_text().replace(":3100/api", ":3102/api").replace(":3100", ":3102")
    tools.write_text(text)
    print("retargeted", d.name)
PY

echo "=== Close CLA-59 ==="
python3 /docker/clawsum/scripts/fix-cla59-avenou-closeout.py

echo "=== DONE ==="
