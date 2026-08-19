#!/usr/bin/env bash
set -euo pipefail
export PATH=/paperclip/.hermes-venv/bin:$PATH
export HOME=/paperclip
export HERMES_HOME=/paperclip/.hermes
cd /paperclip
echo "=== before ==="
hermes config show 2>&1 | sed -n '/API Keys/,/Terminal/p' | head -40
# Prefer Anthropic direct (key already present). Avoid OpenRouter free tier.
hermes config set model.provider anthropic 2>&1 || true
# Try common Hermes keys for default model
for m in \
  anthropic/claude-sonnet-4-6 \
  claude-sonnet-4-6 \
  anthropic/claude-sonnet-4 \
  claude-3-5-sonnet-latest \
  claude-sonnet-4-20250514
 do
  if hermes config set model.default "$m" 2>&1; then
    echo "SET model.default=$m"
    break
  fi
done
# Also write YAML directly as fallback
python3 - <<'PY'
from pathlib import Path
import yaml
p=Path('/paperclip/.hermes/config.yaml')
data=yaml.safe_load(p.read_text()) if p.exists() else {}
if not isinstance(data, dict): data={}
# preserve existing dashboard/plugins/display
model=data.setdefault('model', {})
if not isinstance(model, dict): model={}; data['model']=model
model['provider']='anthropic'
# Hermes often wants bare model id for anthropic provider
model['default']=model.get('default') or 'claude-sonnet-4-20250514'
# keep theme bits
p.write_text(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))
print('wrote', p)
print(p.read_text())
PY
echo "=== after ==="
hermes config show 2>&1 | sed -n '/API Keys/,/Terminal/p' | head -40
# Ensure Anthropic key exists in hermes .env (already shown)
if [[ -f /paperclip/.hermes/.env ]]; then
  echo "hermes .env keys:"; grep -E '^[A-Z0-9_]+=' /paperclip/.hermes/.env | cut -d= -f1
fi
echo HERMES_MODEL_FIXED
