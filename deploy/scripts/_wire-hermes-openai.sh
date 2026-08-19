#!/usr/bin/env bash
set -euo pipefail
# Wire Hermes CEO chat to OpenAI (ChatGPT API) with an explicit default model.
ROOT=/docker/clawsum
HERMES_ENV=/docker/clawsum/paperclip-data/.hermes/.env
mkdir -p /docker/clawsum/paperclip-data/.hermes

OPENAI_KEY=$(grep -E '^OPENAI_API_KEY=' "$ROOT/.env" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
ANTHROPIC_KEY=$(grep -E '^ANTHROPIC_API_KEY=' "$ROOT/.env" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
if [[ -z "${OPENAI_KEY}" ]]; then
  echo 'OPENAI_API_KEY missing in host .env'
  exit 1
fi

touch "$HERMES_ENV"
grep -vE '^(OPENAI_API_KEY|ANTHROPIC_API_KEY|OPENROUTER_API_KEY)=' "$HERMES_ENV" > "$HERMES_ENV.tmp" || true
mv "$HERMES_ENV.tmp" "$HERMES_ENV"
printf 'OPENAI_API_KEY=%s\n' "$OPENAI_KEY" >> "$HERMES_ENV"
if [[ -n "${ANTHROPIC_KEY}" ]]; then
  printf 'ANTHROPIC_API_KEY=%s\n' "$ANTHROPIC_KEY" >> "$HERMES_ENV"
fi
chmod 600 "$HERMES_ENV"
docker cp "$HERMES_ENV" clawsum-paperclip-1:/paperclip/.hermes/.env

docker exec -u root clawsum-paperclip-1 bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
export HOME=/paperclip
export HERMES_HOME=/paperclip/.hermes
set -a
# shellcheck disable=SC1091
source /paperclip/.hermes/.env
set +a
python3 - <<PY
from pathlib import Path
import yaml
p = Path("/paperclip/.hermes/config.yaml")
data = yaml.safe_load(p.read_text()) if p.exists() else {}
if not isinstance(data, dict):
    data = {}
model = data.get("model") if isinstance(data.get("model"), dict) else {}
model["provider"] = "openai"
model["default"] = "gpt-5.4"
model["base_url"] = model.get("base_url") or "https://api.openai.com/v1"
data["model"] = model
p.write_text(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))
print("--- config model ---")
print(yaml.safe_dump({"model": data["model"]}, sort_keys=False))
PY
hermes config show 2>&1 | sed -n "/API Keys/,/Display/p" | head -40
'

bash /docker/clawsum/scripts/hermes-dashboard.sh stop || true
sleep 1
bash /docker/clawsum/scripts/hermes-dashboard.sh start
sleep 2
curl -sS -o /dev/null -w "hermes=%{http_code}\n" http://127.0.0.1:9119/ || true
echo CHATGPT_WIRED
