#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
HOST_ENV="$ROOT/.env"
RUNTIME1="$ROOT/paperclip-data/.hermes/clawsum-runtime.env"
RUNTIME2="$ROOT/paperclip-data/.hermes/plugins/clawsum-cockpit/dashboard/clawsum-runtime.env"
RUNTIME3="$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/clawsum-runtime.env"

mkdir -p "$(dirname "$RUNTIME1")" "$(dirname "$RUNTIME2")" 2>/dev/null || true

# Extract needed keys from host .env
python3 <<'PY'
from pathlib import Path
host = Path("/docker/clawsum/.env")
want = {
  "ELEVENLABS_API_KEY",
  "ELEVENLABS_VOICE_ID",
  "ELEVENLABS_TTS_MODEL",
  "ELEVENLABS_API_BASE",
  "SPEECH_TTS_PROVIDER",
  "OPENAI_API_KEY",
  "OPENAI_TTS_MODEL",
  "OPENAI_TTS_VOICE",
  "POSTGRES_HOST",
  "POSTGRES_PORT",
  "POSTGRES_USER",
  "POSTGRES_PASSWORD",
  "POSTGRES_DB",
}
vals = {}
for line in host.read_text(encoding="utf-8", errors="replace").splitlines():
    line=line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k,_,v=line.partition("=")
    k=k.strip()
    if k in want:
        vals[k]=v.strip().strip('"').strip("'")
# defaults
vals.setdefault("SPEECH_TTS_PROVIDER", "elevenlabs")
vals.setdefault("ELEVENLABS_VOICE_ID", "KuQm0Vgf0XGL6Vqko2UY")
vals.setdefault("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2")
vals.setdefault("POSTGRES_HOST", "postgres")
paths = [
 Path("/docker/clawsum/paperclip-data/.hermes/clawsum-runtime.env"),
 Path("/docker/clawsum/paperclip-data/.hermes/plugins/clawsum-cockpit/dashboard/clawsum-runtime.env"),
]
# merge into existing runtime if present
for p in paths:
    existing = {}
    if p.is_file():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line=line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k,_,v=line.partition("=")
            existing[k.strip()]=v.strip()
    existing.update(vals)
    p.parent.mkdir(parents=True, exist_ok=True)
    body="\n".join(f"{k}={existing[k]}" for k in sorted(existing)) + "\n"
    p.write_text(body, encoding="utf-8")
    print("wrote", p, "keys", len(existing), "el_key_len", len(existing.get("ELEVENLABS_API_KEY","")))
PY

# Also copy into live container paths
docker cp "$RUNTIME1" clawsum-paperclip-1:/paperclip/.hermes/clawsum-runtime.env
docker exec clawsum-paperclip-1 mkdir -p /paperclip/.hermes/plugins/clawsum-cockpit/dashboard
docker cp "$RUNTIME2" clawsum-paperclip-1:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/clawsum-runtime.env

bash "$ROOT/scripts/force-restart-hermes-dashboard.sh"
sleep 3
TOKEN=$(tr -d '\r\n' < "$ROOT/paperclip-data/.hermes/dashboard-session.token" 2>/dev/null || true)
H=(-H "X-Hermes-Session-Token: ${TOKEN}")
echo "=== status ==="
curl -sS "${H[@]}" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/tts/status; echo
echo "=== synth ==="
curl -sS -D /tmp/tts3.hdr -o /tmp/jarvis-el2.mp3 "${H[@]}" -H 'Content-Type: application/json' \
  -d '{"text":"Boss, Jarvis is speaking with your ElevenLabs voice now."}' \
  http://127.0.0.1:9119/api/plugins/clawsum-cockpit/tts
grep -iE 'HTTP/|x-clawsum-tts|content-type|content-length' /tmp/tts3.hdr
ls -la /tmp/jarvis-el2.mp3
file /tmp/jarvis-el2.mp3
if head -c 1 /tmp/jarvis-el2.mp3 | grep -q '{'; then head -c 400 /tmp/jarvis-el2.mp3; echo; fi
echo DONE
