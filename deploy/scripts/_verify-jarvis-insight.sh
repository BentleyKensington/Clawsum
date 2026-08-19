#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
TOKEN=$(tr -d '\r\n' < "$ROOT/paperclip-data/.hermes/dashboard-session.token" 2>/dev/null || true)
H=(-H "X-Hermes-Session-Token: ${TOKEN}")
echo "=== kpi ==="
curl -sS "${H[@]}" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/processes/kpi; echo
echo "=== insight ==="
curl -sS "${H[@]}" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/session-startup > /tmp/ss.json
python3 - <<'PY'
import json
d=json.load(open("/tmp/ss.json"))
print("ok", d.get("ok"))
print("insight_md_len", len(d.get("insight_md") or ""))
print("awaiting", (d.get("jarvis") or {}).get("awaiting_boss"))
print((d.get("insight_md") or "")[:500])
PY
echo "=== processes ==="
curl -sS "${H[@]}" "http://127.0.0.1:9119/api/plugins/clawsum-cockpit/processes?limit=3" > /tmp/jp.json
python3 - <<'PY'
import json
d=json.load(open("/tmp/jp.json"))
print([(p.get("title"), p.get("status"), p.get("mode")) for p in (d.get("processes") or [])[:3]])
PY
echo DONE
