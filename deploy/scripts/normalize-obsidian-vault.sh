#!/usr/bin/env bash
# One vault, canonical folder names. Merge empty duplicates; fix ownership.
set -euo pipefail

OBS=/docker/clawsum/obsidian

CANON=(Admin Coding Data RealEstate GHL Comms Research Planning Paperclip)

merge_if_empty() {
  local keep=$1
  local drop=$2
  [[ "$keep" == "$drop" ]] && return 0
  [[ ! -d "$OBS/$drop" ]] && return 0
  if [[ -z "$(find "$OBS/$drop" -mindepth 1 -maxdepth 1 2>/dev/null)" ]]; then
    rmdir "$OBS/$drop" 2>/dev/null || rm -rf "$OBS/$drop"
    echo "Removed empty duplicate: $drop (kept $keep)"
  else
    echo "WARN: $drop not empty — merge manually into $keep"
  fi
}

mkdir -p "$OBS"/{Admin,Coding,Data,RealEstate,GHL,Comms,Research,Planning,Paperclip,_templates,Admin/Reports,Admin/Inbox}

merge_if_empty RealEstate Realestate
merge_if_empty GHL Ghl

for d in "${CANON[@]}" _templates; do
  mkdir -p "$OBS/$d"
done
mkdir -p "$OBS/Admin/Reports" "$OBS/Admin/Inbox"

chown -R 1000:1000 "$OBS"
echo "Obsidian vault normalized under $OBS"
ls -la "$OBS"
