#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum

echo "=== key sources (masked) ==="
python3 <<'PY'
from pathlib import Path
paths = [
 Path("/docker/clawsum/.env"),
 Path("/docker/clawsum/paperclip-data/.hermes/clawsum-runtime.env"),
 Path("/docker/clawsum/paperclip-data/.hermes/plugins/clawsum-cockpit/dashboard/clawsum-runtime.env"),
]
for p in paths:
  if not p.is_file():
    print(p, "MISSING")
    continue
  key=None; vid=None
  for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.startswith("ELEVENLABS_API_KEY="):
      key=line.split("=",1)[1].strip().strip('"').strip("'")
    if line.startswith("ELEVENLABS_VOICE_ID="):
      vid=line.split("=",1)[1].strip().strip('"').strip("'")
  print(f"{p}: key_len={len(key or '')} prefix={(key or '')[:10]}… suffix=…{(key or '')[-4:]} voice={vid}")
PY

KEY=$(grep '^ELEVENLABS_API_KEY=' "$ROOT/.env" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
VID=$(grep '^ELEVENLABS_VOICE_ID=' "$ROOT/.env" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")

echo "=== GET /v1/user ==="
curl -sS -w "\nhttp=%{http_code}\n" -H "xi-api-key: ${KEY}" https://api.elevenlabs.io/v1/user | head -c 800; echo

echo "=== GET /v1/user/subscription ==="
curl -sS -w "\nhttp=%{http_code}\n" -H "xi-api-key: ${KEY}" https://api.elevenlabs.io/v1/user/subscription | python3 -c '
import sys,json
raw=sys.stdin.read()
# last line may be http=
parts=raw.rsplit("\nhttp=",1)
body=parts[0]
code=parts[1].strip() if len(parts)>1 else "?"
print("http", code)
try:
  d=json.loads(body)
except Exception as e:
  print("raw", body[:400]); raise SystemExit
if "detail" in d:
  print("detail", d.get("detail"))
else:
  print("tier", d.get("tier"), "status", d.get("status"))
  print("chars", d.get("character_count"), "/", d.get("character_limit"))
  print("remaining", (d.get("character_limit") or 0)-(d.get("character_count") or 0))
'

echo "=== TTS short (xi-api-key) ==="
curl -sS -D /tmp/el2.hdr -o /tmp/el2.out \
  -H "xi-api-key: ${KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: audio/mpeg" \
  -d "{\"text\":\"Auth check.\",\"model_id\":\"eleven_multilingual_v2\"}" \
  "https://api.elevenlabs.io/v1/text-to-speech/${VID}"
grep -iE 'HTTP/|content-type|content-length' /tmp/el2.hdr | head -8
file /tmp/el2.out
head -c 400 /tmp/el2.out; echo

echo "=== TTS with Authorization Bearer (some keys) ==="
curl -sS -D /tmp/el3.hdr -o /tmp/el3.out \
  -H "Authorization: Bearer ${KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: audio/mpeg" \
  -d "{\"text\":\"Auth check bearer.\",\"model_id\":\"eleven_multilingual_v2\"}" \
  "https://api.elevenlabs.io/v1/text-to-speech/${VID}"
grep -iE 'HTTP/|content-type' /tmp/el3.hdr | head -5
head -c 200 /tmp/el3.out; echo
