#!/usr/bin/env bash
set -euo pipefail
echo "=== api status ==="
curl -sS http://127.0.0.1:9119/api/status
echo
echo "=== paperclip started ==="
docker inspect -f '{{.State.StartedAt}} {{.State.Status}}' clawsum-paperclip-1
echo "=== openclaw started ==="
docker inspect -f '{{.Name}} {{.State.StartedAt}} {{.State.Status}}' clawsum-openclaw-gateway-1 2>/dev/null || true
echo "=== hermes gateway process ==="
docker exec -u root clawsum-paperclip-1 bash -lc 'export PATH=/paperclip/.hermes-venv/bin:/usr/bin:/bin; export HERMES_HOME=/paperclip/.hermes; hermes gateway status; echo ---pidfile---; cat /paperclip/logs/hermes-gateway.pid 2>/dev/null; echo; ls -la /paperclip/logs/hermes-gateway.log 2>/dev/null'
echo "=== hermes config platforms / gateway ==="
docker exec clawsum-paperclip-1 python3 - <<'PY'
from pathlib import Path
p = Path("/paperclip/.hermes/config.yaml")
print("config exists", p.exists(), "size", p.stat().st_size if p.exists() else 0)
text = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
for key in ("platform", "telegram", "discord", "gateway", "messaging"):
    if key in text.lower():
        print("mentions", key)
print("--- first 80 lines ---")
print("\n".join(text.splitlines()[:80]))
PY
echo "=== docker events around Jul 29 if journal ==="
journalctl --since "2026-07-29 00:00" --until "2026-07-30 00:00" -u docker --no-pager 2>/dev/null | sed -n "1,40p" || true
echo "=== paperclip recreate history ==="
docker events --since "2026-07-29T00:00:00" --until "2026-07-30T00:00:00" --filter container=clawsum-paperclip-1 --filter event=die --filter event=start --filter event=destroy 2>/dev/null | sed -n "1,20p" || true
echo "=== hermes gateway install? ==="
docker exec clawsum-paperclip-1 bash -lc 'ls -la /etc/systemd/system/hermes* /paperclip/.config/systemd 2>/dev/null; ls /paperclip/.hermes/ | sed -n "1,40p"'
echo "=== openclaw health ==="
curl -sS -o /dev/null -w "openclaw_ui:%{http_code}\n" http://127.0.0.1:18789/ 2>/dev/null || curl -sS -o /dev/null -w "oc:%{http_code}\n" http://127.0.0.1:18789/healthz 2>/dev/null || true
docker ps --format '{{.Names}} {{.Status}}' | sed -n "1,30p"
