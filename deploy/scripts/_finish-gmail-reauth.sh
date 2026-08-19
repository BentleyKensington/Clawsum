#!/usr/bin/env bash
set -euo pipefail
URL=$(tr -d '\r\n' </tmp/_oauth-redirect-url.txt)
python3 /docker/clawsum/scripts/gmail-reauth-console.py --code "$URL"
echo EXIT:$?
rm -f /tmp/_oauth-redirect-url.txt /tmp/clawsum-gmail-oauth-state.json
python3 /docker/clawsum/scripts/gmail_oauth_health.py
python3 /tmp/_gmail-postcheck.py
