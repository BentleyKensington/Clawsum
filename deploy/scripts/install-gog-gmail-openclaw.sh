#!/usr/bin/env bash
# Wire Clawsum Gmail OAuth (.env) into gog for OpenClaw Control UI / gog skill.
set -eu

ROOT=/docker/clawsum
ENV_FILE="$ROOT/.env"
GOG_BIN="$ROOT/bin/gog"
GOG_HOME="$ROOT/data/.openclaw/gog"
CLIENT_JSON="$ROOT/data/.openclaw/gog-client-secret.json"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source <(grep -E '^GMAIL_|^GOG_' "$ENV_FILE" | tr -d '\r')
set +a

: "${GMAIL_CLIENT_ID:?Set GMAIL_CLIENT_ID in .env}"
: "${GMAIL_CLIENT_SECRET:?Set GMAIL_CLIENT_SECRET in .env}"
: "${GMAIL_REFRESH_TOKEN:?Set GMAIL_REFRESH_TOKEN in .env}"
: "${GMAIL_ADMIN_ADDRESS:=clawsums@gmail.com}"

if [[ ! -x "$GOG_BIN" ]]; then
  echo "Installing gog CLI..."
  mkdir -p "$ROOT/bin"
  ver=$(curl -sS https://api.github.com/repos/openclaw/gogcli/releases/latest | grep -o 'tag_name.: .v[^"]*' | cut -d\" -f4)
  curl -sSL -o /tmp/gog.tgz "https://github.com/openclaw/gogcli/releases/download/${ver}/gogcli_${ver#v}_linux_amd64.tar.gz"
  tar -xzf /tmp/gog.tgz -C "$ROOT/bin" gog
  chmod +x "$GOG_BIN"
fi

python3 "$ROOT/scripts/setup-gog-gmail-openclaw.py"

export GOG_HOME
export GOG_KEYRING_BACKEND="${GOG_KEYRING_BACKEND:-file}"
export GOG_KEYRING_PASSWORD="${GOG_KEYRING_PASSWORD:-clawsum_gog_keyring_change_me}"

mkdir -p "$GOG_HOME"
"$GOG_BIN" auth credentials "$CLIENT_JSON"
"$GOG_BIN" auth import \
  --email "$GMAIL_ADMIN_ADDRESS" \
  --refresh-token-env GMAIL_REFRESH_TOKEN \
  --services gmail \
  --force

chown -R 1000:1000 "$GOG_HOME" "$CLIENT_JSON" 2>/dev/null || true

echo "gog accounts:"
"$GOG_BIN" auth list
echo ""
"$GOG_BIN" auth doctor --check --no-input || true

echo ""
echo "Done. Restart openclaw-gateway and ensure gog is on PATH in the container."
