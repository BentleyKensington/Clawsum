#!/usr/bin/env bash
set -euo pipefail
ST=/tmp/clawsum-tts
ROOT=/docker/clawsum
C=clawsum-paperclip-1
EX="$ROOT/examples/hermes-cockpit"

# Persist voice id + prefer elevenlabs (key may be added later)
if ! grep -q '^ELEVENLABS_VOICE_ID=' "$ROOT/.env" 2>/dev/null; then
  echo 'ELEVENLABS_VOICE_ID=KuQm0Vgf0XGL6Vqko2UY' >> "$ROOT/.env"
else
  sed -i 's/^ELEVENLABS_VOICE_ID=.*/ELEVENLABS_VOICE_ID=KuQm0Vgf0XGL6Vqko2UY/' "$ROOT/.env"
fi
if ! grep -q '^SPEECH_TTS_PROVIDER=' "$ROOT/.env" 2>/dev/null; then
  echo 'SPEECH_TTS_PROVIDER=elevenlabs' >> "$ROOT/.env"
else
  sed -i 's/^SPEECH_TTS_PROVIDER=.*/SPEECH_TTS_PROVIDER=elevenlabs/' "$ROOT/.env"
fi

# Make sure paperclip can read .env keys (plugin_api loads runtime env from host paths too)
cp -f "$ST/plugin_api.py" "$EX/plugin/clawsum-cockpit/dashboard/plugin_api.py"
cp -f "$ST/index.js" "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js"
sed -i 's/\r$//' "$EX/plugin/clawsum-cockpit/dashboard/plugin_api.py" \
  "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js"
docker cp "$EX/plugin/clawsum-cockpit/dashboard/plugin_api.py" \
  "$C:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/plugin_api.py"
docker cp "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js" \
  "$C:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js"
# Also mirror into paperclip-data bind
mkdir -p "$ROOT/paperclip-data/.hermes/plugins/clawsum-cockpit/dashboard/dist"
cp -f "$EX/plugin/clawsum-cockpit/dashboard/plugin_api.py" \
  "$ROOT/paperclip-data/.hermes/plugins/clawsum-cockpit/dashboard/plugin_api.py"
cp -f "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js" \
  "$ROOT/paperclip-data/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js"

bash "$ROOT/scripts/force-restart-hermes-dashboard.sh"
sleep 3
TOKEN=$(tr -d '\r\n' < "$ROOT/paperclip-data/.hermes/dashboard-session.token" 2>/dev/null || true)
H=(-H "X-Hermes-Session-Token: ${TOKEN}")
echo "=== tts status ==="
curl -sS "${H[@]}" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/tts/status; echo
echo "=== tts synth (short) ==="
curl -sS -D /tmp/tts.hdr -o /tmp/tts.mp3 "${H[@]}" -H 'Content-Type: application/json' \
  -d '{"text":"Standing by, Boss. Jarvis voice online."}' \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/tts
head -n 20 /tmp/tts.hdr
ls -la /tmp/tts.mp3
file /tmp/tts.mp3 2>/dev/null || true
echo DONE
