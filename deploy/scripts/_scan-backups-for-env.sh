#!/usr/bin/env bash
set -euo pipefail
echo "=== local backup trees ==="
ls -la /docker/clawsum/data/backups 2>/dev/null | sed -n '1,40p' || true
find /docker/clawsum/data/backups -maxdepth 3 \( -iname '*env*' -o -iname '*secret*' -o -iname '*openrouter*' \) 2>/dev/null | sed -n '1,50p'
echo "=== what's inside latest backup dirs ==="
find /docker/clawsum/data/backups -maxdepth 2 -type d 2>/dev/null | sed -n '1,30p'
# peek file lists in recent snapshots
for d in $(find /docker/clawsum/data/backups -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -5); do
  echo "SNAP $d"
  find "$d" -maxdepth 3 -type f 2>/dev/null | sed -n '1,40p'
done
echo "=== backup-platform.sh include .env? ==="
grep -nE '\.env|openrouter|secret' /docker/clawsum/scripts/backup-platform.sh 2>/dev/null || true
echo "=== rclone/minio clawsum-backups listing ==="
# try list without dumping secrets
if command -v rclone >/dev/null; then
  rclone lsf local:clawsum-backups 2>/dev/null | sed -n '1,30p' || rclone lsd local: 2>/dev/null | sed -n '1,20p' || true
fi
ls -la /backup 2>/dev/null | sed -n '1,30p' || true
find /backup -iname '*env*' 2>/dev/null | sed -n '1,20p' || true
