#!/usr/bin/env bash
set -euo pipefail
ST=/tmp/clawsum-persona-voice
ROOT=/docker/clawsum
CONTAINER=clawsum-paperclip-1
EX="$ROOT/examples/hermes-cockpit"

cp -f "$ST/SOUL.md" "$ST/BOOT.md" "$ST/USER.md" "$EX/"
sed -i 's/\r$//' "$EX/SOUL.md" "$EX/BOOT.md" "$EX/USER.md" "$ST/index.js" 2>/dev/null || true

cp -f "$ST/index.js" "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js"
docker cp "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js" \
  "$CONTAINER:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js"

# Live Hermes persona (what the agent reads)
for f in SOUL.md BOOT.md USER.md; do
  docker cp "$EX/$f" "$CONTAINER:/paperclip/.hermes/$f"
  cp -f "$EX/$f" "$ROOT/paperclip-data/.hermes/$f" 2>/dev/null || true
done

bash "$ROOT/scripts/force-restart-hermes-dashboard.sh"
sleep 1
echo "=== SOUL conversational mode ==="
docker exec "$CONTAINER" grep -n "Conversational mode\|how’s it going\|how.s it going" /paperclip/.hermes/SOUL.md | head -5
echo "=== UI autoplay markers ==="
docker exec "$CONTAINER" grep -c "maybeAutoplayBrief\|brief.autoplayed\|Auto-Speak: On" \
  /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js
echo DONE
