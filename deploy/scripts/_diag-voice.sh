#!/usr/bin/env bash
set +u
set -eo pipefail
CONTAINER=clawsum-paperclip-1

echo "=== hermes voice help/config ==="
docker exec "$CONTAINER" bash -lc '
  export PATH=/paperclip/.hermes-venv/bin:$PATH
  hermes voice --help 2>&1 | head -50
  echo ---
  hermes config --help 2>&1 | head -30
  echo ---
  rg -n "voice|tts|stt|eleven|openai.audio" /paperclip/.hermes/config.yaml 2>/dev/null || true
  echo --- config.yaml ---
  cat /paperclip/.hermes/config.yaml
'

echo "=== voice module / env hints ==="
docker exec "$CONTAINER" bash -lc '
  export PATH=/paperclip/.hermes-venv/bin:$PATH
  rg -n "VOICE|voice_enabled|tts_provider|elevenlabs|speech" \
    /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/voice.py 2>/dev/null | head -40
  echo ---
  rg -n "voice" /paperclip/.hermes/.env 2>/dev/null | sed -E "s/(KEY|TOKEN|SECRET)=.*/\1=***/" || true
  grep -E "ELEVEN|VOICE|TTS|OPENAI" /docker/clawsum/.env 2>/dev/null | sed -E "s/(KEY|TOKEN|SECRET)=.*/\1=***/" || true
'

echo "=== doctor voice bits ==="
docker exec "$CONTAINER" bash -lc '
  export PATH=/paperclip/.hermes-venv/bin:$PATH
  hermes doctor 2>&1 | rg -i "voice|tts|eleven|audio|speech" || true
'
