#!/usr/bin/env bash
set -euo pipefail
# Sync examples → /docker/clawsum, install plugins, ensure OpenAI voice alias, restart dashboard.
ROOT=/docker/clawsum
REPO_STAGING=/tmp/clawsum-hub-ui

rsync -a --delete \
  "${REPO_STAGING}/examples/hermes-cockpit/" \
  "${ROOT}/examples/hermes-cockpit/"

# Also keep wire script available
if [[ -f "${REPO_STAGING}/scripts/_wire-hermes-openai.sh" ]]; then
  cp -f "${REPO_STAGING}/scripts/_wire-hermes-openai.sh" "${ROOT}/scripts/_wire-hermes-openai.sh"
fi

# Alias voice OpenAI key to chat key so Hermes UI shows OpenAI set
HERMES_ENV=/docker/clawsum/paperclip-data/.hermes/.env
if [[ -f "$HERMES_ENV" ]] && grep -q '^OPENAI_API_KEY=' "$HERMES_ENV"; then
  KEY=$(grep -E '^OPENAI_API_KEY=' "$HERMES_ENV" | head -1 | cut -d= -f2-)
  grep -vE '^VOICE_TOOLS_OPENAI_KEY=' "$HERMES_ENV" > "$HERMES_ENV.tmp" || true
  mv "$HERMES_ENV.tmp" "$HERMES_ENV"
  printf 'VOICE_TOOLS_OPENAI_KEY=%s\n' "$KEY" >> "$HERMES_ENV"
  chmod 600 "$HERMES_ENV"
  docker cp "$HERMES_ENV" clawsum-paperclip-1:/paperclip/.hermes/.env
fi

bash "${ROOT}/scripts/install-clawsum-sidebar-plugins.sh"
bash "${ROOT}/scripts/hermes-dashboard.sh" stop || true
sleep 1
bash "${ROOT}/scripts/hermes-dashboard.sh" start
sleep 2
curl -sS -o /dev/null -w "hermes=%{http_code}\n" http://127.0.0.1:9119/ || true
# Spot-check plugin assets
docker exec clawsum-paperclip-1 bash -lc '
test -f /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js
grep -q clawsum-kpi-grid /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js
grep -q clawsum-boss-greet /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js
grep -q AGENT_EXPLAIN /paperclip/.hermes/plugins/clawsum-agents/dashboard/dist/index.js
echo PLUGIN_ASSETS_OK
'
echo HUB_UI_DEPLOYED
