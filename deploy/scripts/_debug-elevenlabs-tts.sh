#!/usr/bin/env bash
set -euo pipefail
echo "=== recent VOICE_TTS logs ==="
docker logs clawsum-paperclip-1 2>&1 | grep -E 'VOICE_TTS' | tail -30 || true
# Also hermes may log to stdout of dashboard process - check paperclip logs more broadly
docker exec clawsum-paperclip-1 sh -c 'ls /paperclip/logs 2>/dev/null; tail -50 /paperclip/logs/*.log 2>/dev/null | grep -E VOICE_TTS | tail -20' || true

TOKEN=$(tr -d '\r\n' < /docker/clawsum/paperclip-data/.hermes/dashboard-session.token)
echo "=== force provider elevenlabs ==="
curl -sS -D /tmp/t4.hdr -o /tmp/t4.out \
  -H "X-Hermes-Session-Token: ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"text":"ElevenLabs direct test one two three.","provider":"elevenlabs"}' \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/tts || true
grep -iE 'HTTP/|x-clawsum|content-type|content-length' /tmp/t4.hdr || cat /tmp/t4.hdr
file /tmp/t4.out
if head -c 1 /tmp/t4.out | grep -q '{'; then echo ERR_BODY; head -c 600 /tmp/t4.out; echo; fi

echo "=== direct curl to ElevenLabs from host ==="
KEY=$(grep '^ELEVENLABS_API_KEY=' /docker/clawsum/.env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
VID=$(grep '^ELEVENLABS_VOICE_ID=' /docker/clawsum/.env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
curl -sS -D /tmp/el.hdr -o /tmp/el.mp3 \
  -H "xi-api-key: ${KEY}" \
  -H 'Content-Type: application/json' \
  -H 'Accept: audio/mpeg' \
  -d "{\"text\":\"Direct ElevenLabs host test.\",\"model_id\":\"eleven_multilingual_v2\"}" \
  "https://api.elevenlabs.io/v1/text-to-speech/${VID}" || true
grep -iE 'HTTP/|content-type|content-length' /tmp/el.hdr | head -10
file /tmp/el.mp3
if head -c 1 /tmp/el.mp3 | grep -q '{'; then head -c 500 /tmp/el.mp3; echo; fi

echo "=== after force, plugin logs ==="
docker logs clawsum-paperclip-1 2>&1 | grep -E 'VOICE_TTS' | tail -15 || true
# hermes dashboard might print to a file
ps aux | grep 'hermes dashboard' | grep -v grep | head -2
echo DONE
