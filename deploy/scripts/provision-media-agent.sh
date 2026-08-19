#!/usr/bin/env bash
# Provision Clawsum Media OpenClaw agent + Paperclip assignee (Phase 0 wiring).
set -euo pipefail
ROOT=/docker/clawsum
cd "$ROOT"

cp -f /tmp/configure-openclaw.py /tmp/wire-paperclip-clawsum.py /tmp/seed-persona-os.sh /tmp/ghl_accounts.py "$ROOT/scripts/" 2>/dev/null || true
# prefer repo copies already synced
for f in configure-openclaw.py wire-paperclip-clawsum.py seed-persona-os.sh ghl_accounts.py; do
  [ -f "/tmp/$f" ] && cp -f "/tmp/$f" "$ROOT/scripts/$f"
done
sed -i 's/\r$//' "$ROOT/scripts/"*.py "$ROOT/scripts/seed-persona-os.sh" 2>/dev/null || true

# skills + docs
mkdir -p "$ROOT/skills" "$ROOT/docs" "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard"
if [ -d /tmp/clawsum-media-skills ]; then
  cp -a /tmp/clawsum-media-skills/. "$ROOT/skills/"
fi
[ -f /tmp/MEDIA-PRODUCTION-STUDIO.md ] && cp -f /tmp/MEDIA-PRODUCTION-STUDIO.md "$ROOT/docs/"
[ -f /tmp/AUTHORITY.md ] && cp -f /tmp/AUTHORITY.md "$ROOT/skills/"
[ -f /tmp/CATALOG.md ] && cp -f /tmp/CATALOG.md "$ROOT/skills/"
[ -f /tmp/authority.json ] && cp -f /tmp/authority.json "$ROOT/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/"
# live hermes plugin path
if [ -d /docker/clawsum/paperclip-data/.hermes/plugins/clawsum-cockpit/dashboard ]; then
  cp -f /tmp/authority.json /docker/clawsum/paperclip-data/.hermes/plugins/clawsum-cockpit/dashboard/ 2>/dev/null || true
fi

echo "=== configure openclaw (adds media) ==="
python3 "$ROOT/scripts/configure-openclaw.py"

echo "=== seed persona (media) ==="
bash "$ROOT/scripts/seed-persona-os.sh" || true

echo "=== wire paperclip agents ==="
python3 "$ROOT/scripts/wire-paperclip-clawsum.py" || true

chown -R 1000:1000 "$ROOT/data/.openclaw" 2>/dev/null || true
echo "MEDIA_PROVISION_DONE"
