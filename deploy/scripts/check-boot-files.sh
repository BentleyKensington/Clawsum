#!/usr/bin/env bash
set -eu
BASE=/docker/clawsum/data/.openclaw
for a in admin coding data ghl comms planning research realestate paperclip; do
  d="$BASE/workspace-$a"
  echo "=== $a ==="
  for f in SOUL.md USER.md DATABASE.md BOOT.md SECURITY.md memory/2026-05-21.md memory/2026-05-22.md; do
    if [[ -f "$d/$f" ]]; then
      echo "  OK $f"
    else
      echo "  MISSING $f"
    fi
  done
done
