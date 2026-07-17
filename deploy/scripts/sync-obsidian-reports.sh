#!/usr/bin/env bash
# Copy daily global reports into Obsidian Admin/Reports/.
set -euo pipefail

REPORTS=/docker/clawsum/data/reports
DEST=/docker/clawsum/obsidian/Admin/Reports

mkdir -p "$DEST"
shopt -s nullglob

count=0
for f in "$REPORTS"/global-*.md; do
  base=$(basename "$f")
  if [[ ! -f "$DEST/$base" ]] || [[ "$f" -nt "$DEST/$base" ]]; then
    cp -p "$f" "$DEST/$base"
    count=$((count + 1))
  fi
done

# Symlink latest for quick open
latest=$(ls -t "$REPORTS"/global-*.md 2>/dev/null | head -1 || true)
if [[ -n "$latest" ]]; then
  ln -sf "Reports/$(basename "$latest")" /docker/clawsum/obsidian/Admin/Latest-Report.md
fi

chown -R 1000:1000 /docker/clawsum/obsidian/Admin/Reports /docker/clawsum/obsidian/Admin/Latest-Report.md 2>/dev/null || true
echo "Obsidian sync: $count report(s) updated → Admin/Reports/"
