#!/usr/bin/env bash
set -euo pipefail
docker exec -u root clawsum-paperclip-1 bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
export HOME=/paperclip
export HERMES_HOME=/paperclip/.hermes
set -a
source /paperclip/.hermes/.env 2>/dev/null || true
set +a
python3 - <<PY
import os
k=os.environ.get("OPENAI_API_KEY","")
a=os.environ.get("ANTHROPIC_API_KEY","")
print("env_openai_len", len(k))
print("env_anthropic_len", len(a))
print("openai_prefix", (k[:7]+"...") if k else "MISSING")
PY
hermes config show 2>&1 | sed -n "1,120p"
echo "---"
# Try common hermes secret setters
hermes config set --help 2>&1 | sed -n "1,60p" || true
echo "---"
ls -la /paperclip/.hermes/ | sed -n "1,40p"
echo "---"
# Look for where Anthropic key is stored
find /paperclip/.hermes -maxdepth 3 -type f \( -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.db" -o -name "*.sqlite*" \) 2>/dev/null | sed -n "1,40p"
'
