#!/usr/bin/env bash
set -eu
echo "=== LAST_SESSION.md host ==="
stat -c '%y %s %n' /docker/clawsum/paperclip-data/.hermes/LAST_SESSION.md 2>/dev/null || true
echo "-----"
cat /docker/clawsum/paperclip-data/.hermes/LAST_SESSION.md 2>/dev/null || echo MISSING
echo
echo "=== LAST_SESSION in container ==="
docker exec clawsum-paperclip-1 stat -c '%y %s' /paperclip/.hermes/LAST_SESSION.md 2>/dev/null || true
echo "=== session-briefs files ==="
ls -lt /docker/clawsum/paperclip-data/.hermes/session-briefs 2>/dev/null | head -15 || true
docker exec clawsum-paperclip-1 ls -lt /paperclip/.hermes/session-briefs 2>/dev/null | head -15 || true
echo "=== gmail admin in env (keys only) ==="
grep -E '^GMAIL_ADMIN_ADDRESS=|^GMAIL_CLIENT_ID=' /docker/clawsum/.env | sed 's/\(CLIENT_ID=\).\{12\}/\1***/'
