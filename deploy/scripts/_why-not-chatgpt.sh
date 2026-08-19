#!/usr/bin/env bash
set -euo pipefail
export PATH=/paperclip/.hermes-venv/bin:$PATH
export HOME=/paperclip
export HERMES_HOME=/paperclip/.hermes
echo "=== hermes config model/keys ==="
hermes config show 2>&1 | sed -n '/API Keys/,/Display/p' | head -50
echo "=== hermes .env key names ==="
if [[ -f /paperclip/.hermes/.env ]]; then
  grep -E '^[A-Z0-9_]+=' /paperclip/.hermes/.env | cut -d= -f1
else
  echo "(no /paperclip/.hermes/.env)"
fi
echo "=== hermes config.yaml model block ==="
python3 - <<'PY'
from pathlib import Path
import yaml
p=Path('/paperclip/.hermes/config.yaml')
d=yaml.safe_load(p.read_text()) if p.exists() else {}
print('model:', d.get('model'))
print('keys top:', list((d or {}).keys()))
PY
echo "=== host clawsum .env LLM keys present? ==="
# paperclip may not see host .env; check from host mount if available
for f in /docker/clawsum/.env /paperclip/../.env; do
  [[ -f $f ]] && echo "FILE $f" && grep -E '^(OPENAI|ANTHROPIC|OPENROUTER|HERMES)' "$f" | cut -d= -f1 || true
done
ls /docker/clawsum/.env 2>/dev/null || ls /paperclip-data 2>/dev/null || true
