#!/usr/bin/env bash
set -euo pipefail
ENV=/docker/clawsum/.env
U=$(grep -E '^BOSS_OPS_AUTH_USER=' "$ENV" | cut -d= -f2- | tr -d '\r')
P=$(grep -E '^BOSS_OPS_AUTH_PASSWORD=' "$ENV" | cut -d= -f2- | tr -d '\r')

echo "=== themes full ==="
curl -sS http://127.0.0.1:9119/api/dashboard/themes | python3 -m json.tool | head -120

echo "=== plugins with cookies / headers ==="
# Try common auth patterns
curl -sS -D- -o /tmp/p.json http://127.0.0.1:9119/api/plugins 2>&1 | head -40
echo BODY:; cat /tmp/p.json; echo

echo "=== find hermes plugin loader ==="
docker exec clawsum-paperclip-1 bash -lc '
  V=/paperclip/.hermes-venv
  find "$V" -name "*.py" 2>/dev/null | xargs grep -l "plugins" 2>/dev/null | head -30
  find "$V" -path "*hermes*" -name "web_server*.py" 2>/dev/null | head
  find "$V" -path "*hermes*" -name "*plugin*" 2>/dev/null | head -40
'

echo "=== config.yaml full + dashboard section docs ==="
docker exec clawsum-paperclip-1 cat /paperclip/.hermes/config.yaml
echo
docker exec clawsum-paperclip-1 bash -lc '
  V=/paperclip/.hermes-venv
  # dump theme names from disk
  ls -la /paperclip/.hermes/dashboard-themes/
  # grep for origin / trusted / plugin path in installed package
  python3 - <<PY
import pathlib
roots=list(pathlib.Path("/paperclip/.hermes-venv/lib").glob("python*/site-packages"))
for r in roots:
  for p in r.rglob("*.py"):
    if "hermes" not in str(p).lower() and "dashboard" not in str(p).lower():
      continue
    try: t=p.read_text(errors="ignore")
    except: continue
    if "origin_mismatch" in t or "trusted_origins" in t or "allow_origins" in t:
      print("ORIGIN", p)
    if "dashboard-themes" in t or "plugins" in t and "manifest" in t:
      if "plugin" in p.name.lower() or "theme" in p.name.lower() or "web_server" in p.name.lower() or "dashboard" in p.name.lower():
        print("PLUGINISH", p)
PY
'
