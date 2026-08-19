#!/bin/bash
python3 /docker/clawsum/scripts/gmail_oauth_health.py --dry-run 2>&1 | head -40
echo "---state---"
cat /docker/clawsum/data/reports/gmail-oauth-health.json 2>/dev/null | head -80
echo "---recent log---"
tail -20 /docker/clawsum/data/reports/gmail-inbox-pipeline.log 2>/dev/null || true
