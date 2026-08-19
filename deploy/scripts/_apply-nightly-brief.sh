#!/usr/bin/env bash
set -euo pipefail
R=/docker/clawsum
sed -i 's/\r$//' /tmp/nightly-last-session.py /tmp/install-nightly-last-session-cron.sh /tmp/install-platform-crons.sh
cp -f /tmp/nightly-last-session.py "$R/scripts/nightly-last-session.py"
cp -f /tmp/install-nightly-last-session-cron.sh "$R/scripts/install-nightly-last-session-cron.sh"
cp -f /tmp/install-platform-crons.sh "$R/scripts/install-platform-crons.sh"
chmod +x "$R/scripts/nightly-last-session.py" "$R/scripts/install-nightly-last-session-cron.sh"
bash "$R/scripts/install-nightly-last-session-cron.sh"
python3 "$R/scripts/nightly-last-session.py"
echo "=== LAST_SESSION head ==="
head -20 "$R/paperclip-data/.hermes/LAST_SESSION.md"
