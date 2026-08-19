#!/usr/bin/env bash
# Install Clawsum Hermes cockpit theme + plugin into the Paperclip/Hermes container.
# Prerequisites: hermes-agent[web] installed; dashboard can be started after this.
set -euo pipefail

CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SRC="${ROOT}/deploy/examples/hermes-cockpit"
# Flat VPS layout may copy examples under /docker/clawsum/examples/
if [[ ! -d "$SRC" ]]; then
  SRC="${ROOT}/examples/hermes-cockpit"
fi
if [[ ! -d "$SRC" ]]; then
  # Dev checkout path
  SRC="$(cd "$(dirname "$0")/../examples/hermes-cockpit" && pwd)"
fi

HERMES_HOME_IN_CT="${HERMES_HOME_IN_CT:-/paperclip/.hermes}"

echo "Source:    ${SRC}"
echo "Container: ${CONTAINER}"
echo "Hermes:    ${HERMES_HOME_IN_CT}"

if [[ ! -f "${SRC}/theme/clawsum-command.yaml" ]]; then
  echo "ERROR: cockpit theme not found at ${SRC}/theme/clawsum-command.yaml" >&2
  exit 1
fi

if ! docker inspect "${CONTAINER}" >/dev/null 2>&1; then
  echo "ERROR: container ${CONTAINER} not found" >&2
  exit 1
fi

docker exec -u root "${CONTAINER}" bash -lc "
  set -euo pipefail
  H='${HERMES_HOME_IN_CT}'
  mkdir -p \"\$H/dashboard-themes\" \"\$H/plugins\" \"\$H/clawsum-assets\"
  # Prefer /root/.hermes if hermes already created it
  if [[ -d /root/.hermes ]]; then
    H=/root/.hermes
    mkdir -p \"\$H/dashboard-themes\" \"\$H/plugins\" \"\$H/clawsum-assets\"
    echo \"Using Hermes home: \$H\"
  fi
  echo \"\$H\" > /tmp/clawsum-hermes-home
"

HERMES_HOME="$(docker exec "${CONTAINER}" cat /tmp/clawsum-hermes-home 2>/dev/null || echo "${HERMES_HOME_IN_CT}")"
echo "Resolved Hermes home: ${HERMES_HOME}"

# Theme
docker cp "${SRC}/theme/clawsum-command.yaml" \
  "${CONTAINER}:${HERMES_HOME}/dashboard-themes/clawsum-command.yaml"

# Plugin tree
docker exec -u root "${CONTAINER}" rm -rf "${HERMES_HOME}/plugins/clawsum-cockpit"
docker cp "${SRC}/plugin/clawsum-cockpit" \
  "${CONTAINER}:${HERMES_HOME}/plugins/clawsum-cockpit"

# Assets next to plugin API + shared dir
docker exec -u root "${CONTAINER}" mkdir -p \
  "${HERMES_HOME}/plugins/clawsum-cockpit/dashboard/assets" \
  "${HERMES_HOME}/clawsum-assets"
docker cp "${SRC}/assets/." \
  "${CONTAINER}:${HERMES_HOME}/plugins/clawsum-cockpit/dashboard/assets/"
docker cp "${SRC}/assets/." \
  "${CONTAINER}:${HERMES_HOME}/clawsum-assets/"

# Soft-link assets path used by plugin_api fallback
docker exec -u root "${CONTAINER}" bash -lc "
  ln -sfn '${HERMES_HOME}/clawsum-assets' /paperclip/.hermes/clawsum-assets 2>/dev/null || true
"

# Proactive SOUL — task list + archive drive (do not overwrite if custom and newer)
if [[ -f "${SRC}/SOUL.md" ]]; then
  docker cp "${SRC}/SOUL.md" "${CONTAINER}:${HERMES_HOME}/SOUL.md"
  docker exec -u root "${CONTAINER}" bash -lc "
    ln -sfn '${HERMES_HOME}/SOUL.md' /paperclip/.hermes/SOUL.md 2>/dev/null || true
  "
  echo "Installed Clawsum SOUL.md (proactive archive + Paperclip drive)"
fi

# Clawsum CLI/TUI skin (ASCII banner + branding — removes Hermes intro art)
# Overlays EVERY builtin skin name so all profiles/skins show Clawsum ASCII.
if [[ -f "${SRC}/skins/clawsum.yaml" ]]; then
  docker exec -u root "${CONTAINER}" mkdir -p "${HERMES_HOME}/skins"
  docker cp "${SRC}/skins/clawsum.yaml" \
    "${CONTAINER}:${HERMES_HOME}/skins/clawsum.yaml"
  echo "Installed Clawsum skin (ASCII + branding)"
fi
if [[ -f "${ROOT}/scripts/ensure-clawsum-ascii-all-profiles.py" ]]; then
  python3 "${ROOT}/scripts/ensure-clawsum-ascii-all-profiles.py" \
    --home "${HERMES_HOME_HOST:-/docker/clawsum/paperclip-data/.hermes}" \
    --template "${SRC}/skins/clawsum.yaml" \
    || python3 "${ROOT}/scripts/ensure-clawsum-ascii-all-profiles.py" \
      --home /docker/clawsum/paperclip-data/.hermes \
      --template "${SRC}/skins/clawsum.yaml"
  echo "Ensured Clawsum ASCII on all Hermes profiles + skin names"
fi

# Persist theme + enable user plugin (Hermes 0.18+ hides tabs unless plugins.enabled)
docker exec -u root "${CONTAINER}" bash -lc "
  set -euo pipefail
  export PATH=\"/paperclip/.hermes-venv/bin:\$PATH\"
  python3 - <<'PY'
from pathlib import Path
try:
    import yaml
except ImportError:
    yaml = None
cfg_path = Path('${HERMES_HOME}') / 'config.yaml'
cfg_path.parent.mkdir(parents=True, exist_ok=True)
raw = cfg_path.read_text() if cfg_path.exists() else ''
data = {}
if yaml:
    try:
        data = yaml.safe_load(raw) or {}
    except Exception:
        data = {}
if not isinstance(data, dict):
    data = {}
dash = data.setdefault('dashboard', {})
if not isinstance(dash, dict):
    dash = {}
    data['dashboard'] = dash
dash['theme'] = 'clawsum-command'
display = data.setdefault('display', {})
if not isinstance(display, dict):
    display = {}
    data['display'] = display
display['skin'] = 'clawsum'
plugins = data.setdefault('plugins', {})
if not isinstance(plugins, dict):
    plugins = {}
    data['plugins'] = plugins
enabled = plugins.get('enabled')
if not isinstance(enabled, list):
    enabled = []
    plugins['enabled'] = enabled
if 'clawsum-cockpit' not in enabled:
    enabled.append('clawsum-cockpit')
disabled = plugins.get('disabled')
if isinstance(disabled, list) and 'clawsum-cockpit' in disabled:
    disabled.remove('clawsum-cockpit')
if yaml:
    cfg_path.write_text(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))
else:
    cfg_path.write_text(
        'dashboard:\\n  theme: clawsum-command\\n'
        'display:\\n  skin: clawsum\\n'
        'plugins:\\n  enabled:\\n    - clawsum-cockpit\\n'
    )
print('Set theme=clawsum-command, display.skin=clawsum, plugins.enabled += clawsum-cockpit')
PY
  hermes plugins enable clawsum-cockpit 2>/dev/null || true
"

echo ""
echo "OK Clawsum cockpit installed."
echo "Restart dashboard:"
echo "  bash ${ROOT}/scripts/hermes-dashboard.sh stop || true"
echo "  bash ${ROOT}/scripts/hermes-dashboard.sh start"
echo ""
echo "Then open Clawsum UI → palette → 'Clawsum Command' (if not auto-selected)."
echo "Tab: Clawsum  |  Chat uses Clawsum skin (ASCII + branding)."
echo ""
echo "Optional .env for data feeds (Paperclip container env):"
echo "  CLAWSUM_BOSS_URL=https://boss.yourdomain.com"
echo "  CLAWSUM_OPENCLAW_URL=https://clawsum.yourdomain.com"
echo "  CLAWSUM_GRAFANA_URL=https://grafana.yourdomain.com"
echo "  CLAWSUM_GRAFANA_EMBED_URL=https://grafana.yourdomain.com/d/clawsum-health?orgId=1&kiosk"
echo "  PAPERCLIP_API=http://127.0.0.1:3100/api"
echo "  PAPERCLIP_COMPANY_ID=..."
echo "  POSTGRES_PASSWORD=..."
echo ""
echo "Doc: deploy/examples/hermes-cockpit/README.md"
