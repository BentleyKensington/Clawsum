#!/usr/bin/env bash
docker exec clawsum-openclaw-gateway-1 bash -lc '
set -eu
id
for a in comms data ghl research planning coding admin realestate paperclip; do
  echo "=== $a ==="
  ls -ld /home/node/.openclaw/agents/$a/sessions 2>&1 || true
  ls -ld /home/node/.openclaw/agents/$a/agent/codex-home 2>&1 || true
  if touch /home/node/.openclaw/agents/$a/sessions/.w 2>/dev/null; then
    rm -f /home/node/.openclaw/agents/$a/sessions/.w
    echo "sessions: writable"
  else
    echo "sessions: NOT writable"
  fi
  if [[ -d /home/node/.openclaw/agents/$a/agent/codex-home ]]; then
    if touch /home/node/.openclaw/agents/$a/agent/codex-home/.w 2>/dev/null; then
      rm -f /home/node/.openclaw/agents/$a/agent/codex-home/.w
      echo "codex-home: writable"
    else
      echo "codex-home: NOT writable"
    fi
  fi
done
'
