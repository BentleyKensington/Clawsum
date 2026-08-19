#!/usr/bin/env bash
# Fix Paperclip host routing so OpenClaw agents can call local API without Authelia.
# Root cause: Paperclip HOST=127.0.0.1 (host network) is unreachable from gateway container;
# agents then hit https://paperclip.clawsum.com and get Authelia 302 → missing disposition.
set -euo pipefail
ROOT=/docker/clawsum
COMPOSE="$ROOT/docker-compose.yml"
ENVF="$ROOT/.env"

echo "=== 1) Patch compose Paperclip HOST -> 0.0.0.0 ==="
python3 - <<'PY'
from pathlib import Path
p = Path("/docker/clawsum/docker-compose.yml")
text = p.read_text()
old = 'HOST: "127.0.0.1"'
new = 'HOST: "0.0.0.0"  # reachable from openclaw-gateway via host.docker.internal'
# only replace within paperclip service block — first HOST after paperclip: is paperclip
idx = text.find("  paperclip:")
if idx < 0:
    raise SystemExit("paperclip service not found")
# find HOST after paperclip
h = text.find('HOST: "127.0.0.1"', idx)
if h < 0:
    if 'HOST: "0.0.0.0"' in text[idx:idx+800]:
        print("already 0.0.0.0")
    else:
        raise SystemExit("HOST line not found near paperclip")
else:
    # ensure this HOST is before next service at same indent level after paperclip env
    text = text[:h] + new + text[h+len(old):]
    p.write_text(text)
    print("patched HOST to 0.0.0.0")
PY

echo "=== 2) Ensure .env agent API URL ==="
grep -q '^PAPERCLIP_AGENT_API_URL=' "$ENVF" 2>/dev/null && \
  sed -i 's|^PAPERCLIP_AGENT_API_URL=.*|PAPERCLIP_AGENT_API_URL=http://host.docker.internal:3100/api|' "$ENVF" || \
  echo 'PAPERCLIP_AGENT_API_URL=http://host.docker.internal:3100/api' >> "$ENVF"
# Prefer 3100 primary; recovery 3101 noted separately
grep -q '^PAPERCLIP_API=' "$ENVF" || echo 'PAPERCLIP_API=http://127.0.0.1:3100/api' >> "$ENVF"
grep -E 'PAPERCLIP_AGENT_API_URL|PAPERCLIP_API=' "$ENVF" | head -5

echo "=== 3) Inject PAPERCLIP_API_URL into openclaw-gateway env in compose ==="
python3 - <<'PY'
from pathlib import Path
p = Path("/docker/clawsum/docker-compose.yml")
text = p.read_text()
needle = "      X_CB_KEY: ${X_CB_KEY:-}"
inject = """      X_CB_KEY: ${X_CB_KEY:-}
      # Agent→Paperclip callback (never use public Authelia URL from inside gateway)
      PAPERCLIP_API_URL: ${PAPERCLIP_AGENT_API_URL:-http://host.docker.internal:3100/api}
      PAPERCLIP_RUNTIME_API_URL: ${PAPERCLIP_AGENT_API_URL:-http://host.docker.internal:3100/api}"""
if "PAPERCLIP_API_URL:" in text and "host.docker.internal:3100" in text:
    print("gateway env already has PAPERCLIP_API_URL")
elif needle in text:
    text = text.replace(needle, inject, 1)
    p.write_text(text)
    print("injected PAPERCLIP_API_URL into openclaw-gateway")
else:
    print("WARN: could not find X_CB_KEY anchor; manual check needed")
PY

echo "=== 4) Write agent PAPERCLIP tools note (ghl-ave-rei + all ghl-*) ==="
python3 - <<'PY'
from pathlib import Path
note = """
## Paperclip API (agents)

Use the **local** API from this container — never the public Authelia hostname.

```bash
export PAPERCLIP_API_URL="${PAPERCLIP_API_URL:-http://host.docker.internal:3100/api}"
curl -sS "$PAPERCLIP_API_URL/agents/me"
```

Forbidden for API closeout (returns Authelia 302):
- `https://paperclip.clawsum.com/api/...`

Recovery runtime (if Hermes spun Paperclip on :3101):
- `http://host.docker.internal:3101/api`

After a successful run you MUST:
1. POST work-products on the issue
2. POST a short comment with artifact paths
3. PATCH issue status to `done` (or `blocked` with a clear next step)
"""
base = Path("/docker/clawsum/data/.openclaw")
for d in base.glob("workspace-ghl*"):
    tools = d / "TOOLS.md"
    if not tools.exists():
        tools.write_text("# TOOLS.md\n" + note)
        print("created", tools)
        continue
    text = tools.read_text()
    if "host.docker.internal:3100" in text:
        print("ok", d.name)
        continue
    tools.write_text(text.rstrip() + "\n" + note)
    print("updated", d.name)
# also slack-avenou if present
for d in [base / "workspace-slack-avenou"]:
    if d.is_dir():
        tools = d / "TOOLS.md"
        text = tools.read_text() if tools.exists() else "# TOOLS.md\n"
        if "host.docker.internal:3100" not in text:
            tools.write_text(text.rstrip() + "\n" + note)
            print("updated", d.name)
PY

echo "=== 5) Recreate paperclip (HOST 0.0.0.0) ==="
cd "$ROOT"
# Stop hermes-spawned duplicate on 3101 if present (same instance dir — dual writers are unsafe)
if ss -lntp | grep -q ':3101'; then
  echo "Stopping recovery Paperclip on :3101 (will use primary :3100 with fixed bind)"
  # child of hermes dashboard — kill only the node on 3101
  pid=$(ss -lntp | sed -n 's/.*:3101 .*pid=\([0-9]*\).*/\1/p' | head -1)
  if [ -n "${pid:-}" ]; then
    echo "kill $pid"
    kill "$pid" || true
    sleep 2
  fi
fi

docker compose --profile orchestration up -d --force-recreate paperclip
sleep 8
ss -lntp | grep -E ':(3100|3101)\b' || true

echo "=== 6) Recreate gateway with PAPERCLIP_API_URL ==="
docker compose up -d --force-recreate openclaw-gateway
sleep 12

echo "=== 7) Verify gateway -> Paperclip ==="
docker exec clawsum-openclaw-gateway-1 sh -c '
  echo PAPERCLIP_API_URL=$PAPERCLIP_API_URL
  for u in http://host.docker.internal:3100/api/health http://host.docker.internal:3100/api/agents/me; do
    echo -n "$u => "
    curl -sS -m 5 -o /tmp/out -w "%{http_code}" "$u" || echo fail
    echo
    head -c 160 /tmp/out; echo
  done
'

echo "=== 8) Close CLA-59 ==="
python3 /docker/clawsum/scripts/fix-cla59-avenou-closeout.py

echo "=== DONE ==="
