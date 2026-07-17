#!/bin/bash
# Single gate: is this VPS template-ready / healthy?
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
cd "$ROOT"
FAIL=0

pass() { echo "OK   $*"; }
fail() { echo "FAIL $*"; FAIL=1; }

echo "=== Clawsum platform verify ==="

curl -sf http://127.0.0.1:${OPENCLAW_GATEWAY_PORT:-48166}/healthz >/dev/null \
  && pass "OpenClaw gateway healthz" || fail "OpenClaw gateway healthz"

curl -sf http://127.0.0.1:3100/api/health >/dev/null \
  && pass "Paperclip API health" || fail "Paperclip API health (is orchestration profile up?)"

docker exec clawsum-postgres-1 pg_isready -U clawsum >/dev/null 2>&1 \
  && pass "Postgres" || fail "Postgres"

python3 - <<'PY' || fail "openclaw.json agents"
import json
from pathlib import Path
p = Path("/docker/clawsum/data/.openclaw/openclaw.json")
if not p.exists():
    raise SystemExit("missing")
n = len(json.loads(p.read_text()).get("agents", {}).get("list", []))
print(f"agents={n}")
if n < 9:
    raise SystemExit("too few agents")
PY
pass "openclaw.json agent count"

[[ -f deploy/examples/instance-overlays/REI-GHL-AGENT-PLAYBOOK.md ]] \
  && pass "GHL instance overlay example present" || echo "INFO no GHL instance overlay example"

python3 scripts/verify-ghl-isolation.py >/dev/null 2>&1 \
  && pass "GHL isolation" || echo "WARN GHL isolation (skip if no GHL credentials)"

bash scripts/telegram-smoke-test.sh >/dev/null 2>&1 \
  && pass "Telegram smoke script" || fail "Telegram smoke script"

# Tier 2 placeholders — fail until implemented
docker compose --profile storage ps --status running 2>/dev/null | grep -q minio \
  && pass "MinIO running" || fail "MinIO running (run deploy-tier2.sh)"

docker compose --profile orchestration ps --status running 2>/dev/null | grep -q langgraph \
  && pass "LangGraph running" || fail "LangGraph running (run deploy-tier2.sh)"

bash scripts/verify-tier2.sh >/dev/null 2>&1 \
  && pass "Tier 2 full verify" || fail "Tier 2 verify (see scripts/verify-tier2.sh)"

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Tier 0/1/2 verify PASSED ==="
  exit 0
else
  echo "=== VERIFY FAILED ==="
  exit 1
fi
