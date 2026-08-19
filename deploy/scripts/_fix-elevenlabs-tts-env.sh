#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
# Show how key is stored (masked)
python3 <<'PY'
from pathlib import Path
p=Path("/docker/clawsum/.env")
for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
    if "ELEVENLABS" in line or "SPEECH_TTS" in line:
        if "API_KEY" in line:
            k,_,v=line.partition("=")
            v=v.strip().strip('"').strip("'")
            print(f"{k.strip()}=*** len={len(v)} empty={not bool(v)}")
        else:
            print(line)
PY

# Restart Hermes so plugin_api reloads .env cache
bash "$ROOT/scripts/force-restart-hermes-dashboard.sh"
sleep 3
TOKEN=$(tr -d '\r\n' < "$ROOT/paperclip-data/.hermes/dashboard-session.token" 2>/dev/null || true)
H=(-H "X-Hermes-Session-Token: ${TOKEN}")
echo "=== status after restart ==="
curl -sS "${H[@]}" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/tts/status; echo
echo "=== synth ==="
curl -sS -D /tmp/tts2.hdr -o /tmp/jarvis-el.mp3 "${H[@]}" -H 'Content-Type: application/json' \
  -d '{"text":"Gerald, this is your Jarvis ElevenLabs voice."}' \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/tts
grep -iE 'HTTP/|x-clawsum-tts|content-type|content-length' /tmp/tts2.hdr
ls -la /tmp/jarvis-el.mp3
file /tmp/jarvis-el.mp3
# if still openai, probe plugin env load path
if grep -qi 'openai' /tmp/tts2.hdr; then
  echo "=== debug env load from plugin paths ==="
  docker exec clawsum-paperclip-1 python3 - <<'PY'
from pathlib import Path
cands=[
 Path("/paperclip/.hermes/clawsum-runtime.env"),
 Path("/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/clawsum-runtime.env"),
 Path("/docker/clawsum/.env"),
]
for p in cands:
  print(p, "exists", p.is_file())
  if p.is_file():
    for line in p.read_text(errors="replace").splitlines():
      if line.startswith("ELEVENLABS_API_KEY="):
        v=line.split("=",1)[1].strip().strip('"').strip("'")
        print("  key_len", len(v))
PY
fi
echo DONE
