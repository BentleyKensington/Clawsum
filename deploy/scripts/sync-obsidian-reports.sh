#!/usr/bin/env bash
# Copy global reports and inbox reviews into Obsidian.
set -euo pipefail

REPORTS=/docker/clawsum/data/reports
INBOX=/docker/clawsum/data/inbox-reports
DEST=/docker/clawsum/obsidian/Admin/Reports
INBOX_DEST=/docker/clawsum/obsidian/Admin/Inbox

mkdir -p "$DEST" "$INBOX_DEST"
shopt -s nullglob

count=0
for f in "$REPORTS"/global-*.md; do
  base=$(basename "$f")
  if [[ ! -f "$DEST/$base" ]] || [[ "$f" -nt "$DEST/$base" ]]; then
    cp -p "$f" "$DEST/$base"
    count=$((count + 1))
  fi
done

inbox_count=0
for f in "$INBOX"/*.md; do
  base=$(basename "$f")
  if [[ ! -f "$INBOX_DEST/$base" ]] || [[ "$f" -nt "$INBOX_DEST/$base" ]]; then
    cp -p "$f" "$INBOX_DEST/$base"
    inbox_count=$((inbox_count + 1))
  fi
done

# Symlink latest for quick open
latest=$(ls -t "$REPORTS"/global-*.md 2>/dev/null | head -1 || true)
if [[ -n "$latest" ]]; then
  ln -sf "Reports/$(basename "$latest")" /docker/clawsum/obsidian/Admin/Latest-Report.md
fi

latest_inbox=$(ls -t "$INBOX"/*.md 2>/dev/null | head -1 || true)
if [[ -n "$latest_inbox" ]]; then
  ln -sf "Inbox/$(basename "$latest_inbox")" /docker/clawsum/obsidian/Admin/Latest-Inbox.md
fi

chown -R 1000:1000 \
  /docker/clawsum/obsidian/Admin/Reports \
  /docker/clawsum/obsidian/Admin/Inbox \
  /docker/clawsum/obsidian/Admin/Latest-Report.md \
  /docker/clawsum/obsidian/Admin/Latest-Inbox.md 2>/dev/null || true
echo "Obsidian sync: ${count} report(s), ${inbox_count} inbox file(s) updated"
