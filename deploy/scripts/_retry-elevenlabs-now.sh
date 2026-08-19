#!/usr/bin/env bash
set -euo pipefail
bash /tmp/_recheck-elevenlabs-auth.sh || true

echo "=== cockpit /tts ==="
TOKEN=$(tr -d '\r\n' < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)
curl -sS -D /tmp/tts-now.hdr -o /tmp/tts-now.mp3 \
  -H "X-Hermes-Session-Token: ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Boss, Jarvis ElevenLabs voice check.","provider":"elevenlabs"}' \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/tts
grep -iE 'HTTP/|x-clawsum-tts|content-type|content-length' /tmp/tts-now.hdr || true
file /tmp/tts-now.mp3
if head -c 1 /tmp/tts-now.mp3 | grep -q '{'; then head -c 400 /tmp/tts-now.mp3; echo; fi
echo DONE
