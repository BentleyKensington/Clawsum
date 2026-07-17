#!/usr/bin/env bash
# Re-sync Codex OAuth + OpenAI API key + daily memory stubs; restart gateway.
set -eu
cd /docker/clawsum

echo "=== memory stubs (Chicago TZ) ==="
TZ=America/Chicago bash scripts/seed-memory-files.sh

echo "=== codex auth sync ==="
python3 scripts/sync-codex-auth-all-agents.py

echo "=== openai api key fallback ==="
bash scripts/sync-openai-api-key-auth.sh

echo "=== llm policy (codex first + openrouter escalation) ==="
python3 scripts/enforce-llm-codex-first.py || true

echo "=== auth.order check ==="
python3 - <<'PY'
import json
from pathlib import Path
c = json.loads(Path("data/.openclaw/openclaw.json").read_text())
order = c.get("auth", {}).get("order", {})
print("auth.order:", json.dumps(order, indent=2))
for aid in ["admin", "coding", "data", "ghl", "comms", "planning"]:
    p = Path(f"data/.openclaw/agents/{aid}/agent/auth-profiles.json")
    if not p.exists():
        print(f"MISSING {p}")
        continue
    d = json.loads(p.read_text())
    profs = list((d.get("profiles") or {}).keys())
    print(f"{aid}: {profs}")
PY

echo "=== restart gateway ==="
docker compose restart openclaw-gateway
sleep 8
docker exec clawsum-openclaw-gateway-1 curl -sS -o /dev/null -w "healthz=%{http_code}\n" http://127.0.0.1:18789/healthz

echo "Done."
