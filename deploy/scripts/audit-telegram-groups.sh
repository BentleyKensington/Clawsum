#!/usr/bin/env bash
# Audit Telegram bindings, auth, memory, and recent session errors per agent.
set -eu
BASE=/docker/clawsum/data/.openclaw
CONFIG="$BASE/openclaw.json"
TODAY=$(TZ=America/Chicago date +%Y-%m-%d)
YDAY=$(TZ=America/Chicago date -d yesterday +%Y-%m-%d 2>/dev/null || true)

echo "=== Gateway ==="
docker ps --filter name=openclaw-gateway --format '{{.Names}} {{.Status}}'
docker exec clawsum-openclaw-gateway-1 curl -sS -o /dev/null -w 'healthz=%{http_code}\n' http://127.0.0.1:18789/healthz 2>/dev/null || echo "healthz FAILED"

echo ""
echo "=== Telegram bindings (openclaw.json) ==="
python3 - <<'PY'
import json
from pathlib import Path
c = json.loads(Path("/docker/clawsum/data/.openclaw/openclaw.json").read_text())
bindings = c.get("bindings", {}).get("telegram", []) or c.get("channels", {}).get("telegram", {}).get("bindings", [])
if not bindings:
    # try alternate shapes
    tg = c.get("channels", {}).get("telegram", {})
    bindings = tg.get("groups", {}) if isinstance(tg.get("groups"), list) else []
    if isinstance(tg.get("groups"), dict):
        for gid, cfg in tg["groups"].items():
            print(f"group {gid} -> {cfg}")
    sessions = Path("/docker/clawsum/data/.openclaw/telegram/sessions.json")
    if sessions.exists():
        print("\n--- telegram/sessions.json ---")
        print(sessions.read_text()[:4000])
for b in bindings if isinstance(bindings, list) else []:
    print(b)
# agents list
agents = c.get("agents", {}).get("list", c.get("agents", []))
if isinstance(agents, list):
    print("\n--- agents ---")
    for a in agents:
        if isinstance(a, dict):
            print(f"  {a.get('id')}: {a.get('name')}")
PY

echo ""
echo "=== sessions.json bindings file ==="
if [[ -f "$BASE/telegram/sessions.json" ]]; then
  python3 -m json.tool "$BASE/telegram/sessions.json" 2>/dev/null | head -80
elif [[ -f "$BASE/credentials/telegram-sessions.json" ]]; then
  python3 -m json.tool "$BASE/credentials/telegram-sessions.json" 2>/dev/null | head -80
else
  find "$BASE" -name '*session*' -path '*telegram*' 2>/dev/null | head -10
fi

echo ""
echo "=== Per-agent: memory yesterday/today, auth, latest session error ==="
AGENTS=(admin coding data realestate ghl comms research planning paperclip)
for a in "${AGENTS[@]}"; do
  echo "--- $a ---"
  ws="$BASE/workspace-$a"
  for d in "$YDAY" "$TODAY"; do
    [[ -z "$d" ]] && continue
    f="$ws/memory/${d}.md"
    [[ -f "$f" ]] && echo "  memory OK $d" || echo "  memory MISSING $d"
  done
  auth="$BASE/agents/$a/agent/auth-profiles.json"
  if [[ -f "$auth" ]]; then
    python3 -c "import json; d=json.load(open('$auth')); print('  auth:', list(d.get('profiles',{}).keys()))"
  else
    echo "  auth MISSING"
  fi
  sess=$(ls -t "$BASE/agents/$a/sessions/"*.jsonl 2>/dev/null | grep -v trajectory | head -1 || true)
  if [[ -n "$sess" ]]; then
    echo "  session: $(basename "$sess")"
    grep -E 'isError.:true|went wrong|api.key|Missing|ENOENT|rate|auth|failed|error' "$sess" 2>/dev/null | tail -2 || echo "  (no obvious errors in session)"
  else
    echo "  session: none"
  fi
done

echo ""
echo "=== Gateway log (telegram/errors, last 40) ==="
docker exec clawsum-openclaw-gateway-1 sh -c '
  for f in /tmp/openclaw/openclaw-2026-05-22.log /tmp/openclaw/openclaw-2026-05-21.log; do
    [[ -f "$f" ]] && grep -iE "telegram|error|fail|binding|agent" "$f" | tail -20
  done
' 2>/dev/null || true

echo ""
echo "=== Telegram getUpdates probe (pending?) ==="
docker exec clawsum-openclaw-gateway-1 node -e "
const token=process.env.TELEGRAM_BOT_TOKEN||require('fs').readFileSync('/docker/clawsum/.env','utf8').match(/TELEGRAM_BOT_TOKEN=(.+)/)?.[1];
" 2>/dev/null || echo "(skip token probe)"

PY
