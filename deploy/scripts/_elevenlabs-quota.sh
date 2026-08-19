#!/usr/bin/env bash
set -euo pipefail
KEY=$(grep '^ELEVENLABS_API_KEY=' /docker/clawsum/.env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
echo "key_prefix=${KEY:0:8}... len=${#KEY}"
echo "=== user/subscription ==="
curl -sS -H "xi-api-key: ${KEY}" https://api.elevenlabs.io/v1/user/subscription | python3 -c '
import sys,json
d=json.load(sys.stdin)
if isinstance(d,dict) and d.get("detail"):
  print("ERR", d)
else:
  print("tier:", d.get("tier") or d.get("plan"))
  print("status:", d.get("status"))
  print("character_count:", d.get("character_count"))
  print("character_limit:", d.get("character_limit"))
  print("remaining:", (d.get("character_limit") or 0) - (d.get("character_count") or 0))
  print("next_reset:", d.get("next_character_count_reset_unix"))
  print("can_extend:", d.get("can_extend_character_limit"))
'
echo "=== user ==="
curl -sS -H "xi-api-key: ${KEY}" https://api.elevenlabs.io/v1/user | python3 -c '
import sys,json
d=json.load(sys.stdin)
print("subscription_keys", list((d.get("subscription") or {}).keys())[:12] if isinstance(d,dict) else d)
sub=d.get("subscription") or {}
print("tier", sub.get("tier"), "chars", sub.get("character_count"), "/", sub.get("character_limit"))
'
