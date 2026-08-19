#!/usr/bin/env bash
set -euo pipefail
docker exec clawsum-paperclip-1 bash -lc '
command -v rg >/dev/null && RG=rg || RG=grep
cd /paperclip/.hermes/tui-prebuilt 2>/dev/null || cd /paperclip/.hermes || exit 0
echo "=== search send/composer ==="
find . -type f \( -name "*.tsx" -o -name "*.ts" -o -name "*.jsx" -o -name "*.vue" \) \
  ! -path "*/node_modules/*" 2>/dev/null \
  | head -5
find packages -type f \( -name "*.tsx" -o -name "*.ts" \) ! -path "*/node_modules/*" 2>/dev/null \
  | xargs grep -l -E "Send message|aria-label=.Send|Composer|chat input|submitMessage" 2>/dev/null \
  | head -30
'
