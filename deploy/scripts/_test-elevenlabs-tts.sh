#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
TOKEN=$(tr -d '\r\n' < "$ROOT/paperclip-data/.hermes/dashboard-session.token" 2>/dev/null || true)
H=(-H "X-Hermes-Session-Token: ${TOKEN}")

echo "=== .env elevenlabs ==="
grep -E '^ELEVENLABS_|^SPEECH_TTS' "$ROOT/.env" 2>/dev/null | sed -E 's/(API_KEY=).*/\1***/; s/(VOICE_ID=)(.*)/\1\2/' || true

echo "=== tts/status ==="
curl -sS "${H[@]}" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/tts/status; echo

echo "=== synthesize short line ==="
curl -sS -D /tmp/tts-hdr.txt -o /tmp/jarvis-tts.mp3 "${H[@]}" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Standing by, Boss. Jarvis ElevenLabs voice check."}' \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/tts
echo "--- headers ---"
grep -iE 'HTTP/|content-type|x-clawsum-tts|content-length' /tmp/tts-hdr.txt || head -20 /tmp/tts-hdr.txt
echo "--- file ---"
ls -la /tmp/jarvis-tts.mp3
file /tmp/jarvis-tts.mp3 2>/dev/null || true
# If JSON error body, show it
if head -c 1 /tmp/jarvis-tts.mp3 | grep -q '{'; then
  echo "BODY (error json):"
  head -c 500 /tmp/jarvis-tts.mp3; echo
fi
echo DONE
