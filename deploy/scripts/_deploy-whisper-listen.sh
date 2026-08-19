#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
ST=/tmp/clawsum-whisper-listen
CONTAINER=clawsum-paperclip-1
DEST="$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard"

cp -f "$ST/plugin_api.py" "$DEST/plugin_api.py"
cp -f "$ST/index.js" "$DEST/dist/index.js"
cp -f "$ST/style.css" "$DEST/dist/style.css"
sed -i 's/\r$//' "$DEST/plugin_api.py" "$DEST/dist/index.js" "$DEST/dist/style.css" 2>/dev/null || true

docker cp "$DEST/plugin_api.py" "$CONTAINER:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/plugin_api.py"
docker cp "$DEST/dist/index.js" "$CONTAINER:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js"
docker cp "$DEST/dist/style.css" "$CONTAINER:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/style.css"

echo "=== OPENAI_API_KEY in paperclip ==="
docker exec "$CONTAINER" bash -lc 'if [[ -n "${OPENAI_API_KEY:-}" ]]; then echo OPENAI_API_KEY=set len=${#OPENAI_API_KEY}; else echo OPENAI_API_KEY=MISSING; fi'

# If missing in container but present on host .env, inject into hermes env + remind
if ! docker exec "$CONTAINER" bash -lc '[[ -n "${OPENAI_API_KEY:-}" ]]'; then
  if grep -qE '^OPENAI_API_KEY=.+' "$ROOT/.env" 2>/dev/null; then
    echo "WARNING: key on host .env but not in running container — restart paperclip to pick up compose env"
  else
    echo "WARNING: OPENAI_API_KEY missing — Whisper will 503"
  fi
fi

bash "$ROOT/scripts/force-restart-hermes-dashboard.sh"
sleep 2

TOKEN=$(tr -d '\r\n' < "$ROOT/paperclip-data/.hermes/dashboard-session.token" 2>/dev/null || true)
if [[ -z "$TOKEN" ]]; then
  TOKEN=$(docker exec "$CONTAINER" bash -lc 'tr -d "\r\n" < /paperclip/.hermes/dashboard-session.token 2>/dev/null' || true)
fi

echo "=== probe index.js markers ==="
docker exec "$CONTAINER" bash -lc 'grep -c "whisper_upload\|data-mic-level\|/transcribe" /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js'

echo "=== probe plugin_api transcribe ==="
docker exec "$CONTAINER" bash -lc 'grep -c "def transcribe_audio\|whisper-1" /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/plugin_api.py'

if [[ -n "$TOKEN" ]]; then
  echo "=== OPTIONS/route check via status ==="
  curl -sS -o /dev/null -w "dashboard:%{http_code}\n" http://127.0.0.1:9119/api/status
  # empty multipart should 400 not 404
  code=$(curl -sS -o /tmp/tr.json -w "%{http_code}" -X POST \
    -H "X-Hermes-Session-Token: $TOKEN" \
    http://127.0.0.1:9119/api/plugins/clawsum-cockpit/transcribe || true)
  echo "transcribe_empty_http:$code"
  head -c 200 /tmp/tr.json; echo
fi
echo DONE
