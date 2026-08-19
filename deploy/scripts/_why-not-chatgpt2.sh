#!/usr/bin/env bash
set -euo pipefail
echo "=== /docker/clawsum/.env LLM keys ==="
if [[ -f /docker/clawsum/.env ]]; then
  grep -E 'OPENAI|ANTHROPIC|OPENROUTER|CODEX' /docker/clawsum/.env | sed 's/=.*/=***/'
else
  echo missing
fi
echo "=== hermes env files ==="
find /docker/clawsum/paperclip-data -name '.env' 2>/dev/null
echo "=== paperclip container env ==="
docker exec clawsum-paperclip-1 bash -lc 'for k in ANTHROPIC_API_KEY OPENAI_API_KEY OPENROUTER_API_KEY; do eval v=\${$k-}; if [[ -n "$v" ]]; then echo "$k=set"; else echo "$k=missing"; fi; done'
echo "=== where anthropic key lives for hermes ==="
docker exec clawsum-paperclip-1 bash -lc 'export PATH=/paperclip/.hermes-venv/bin:$PATH; hermes config env-path; ls -la "$(hermes config env-path 2>/dev/null)" 2>/dev/null; python3 - <<"PY"
from pathlib import Path
import os
# hermes often stores secrets via keyring/env helper
cands=[
 Path("/paperclip/.hermes/.env"),
 Path("/root/.hermes/.env"),
 Path("/paperclip/.env"),
]
for p in cands:
 print(p, "exists" if p.exists() else "no")
PY
find /paperclip -name ".env" 2>/dev/null | head
'
