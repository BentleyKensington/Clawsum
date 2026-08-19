#!/usr/bin/env bash
set -euo pipefail
docker exec clawsum-paperclip-1 bash -lc '
echo "== hermes home =="
ls /paperclip/.hermes | head
echo "== find dashboard static =="
find /paperclip/.hermes -maxdepth 4 -type d \( -name dist -o -name static -o -name assets -o -name dashboard \) 2>/dev/null | head -40
echo "== grep Send in js bundles =="
find /paperclip/.hermes -type f \( -name "*.js" -o -name "*.mjs" \) ! -path "*/node_modules/*" ! -path "*/tui-prebuilt/node_modules/*" 2>/dev/null \
  | while read f; do
      if grep -q "Send message\|aria-label=\"Send\"\|placeholder=.*message\|ProseMirror" "$f" 2>/dev/null; then
        echo "$f"
      fi
    done | head -40
'
