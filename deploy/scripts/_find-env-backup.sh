#!/usr/bin/env bash
set -euo pipefail
echo "=== backup smoke log ==="
sed -n '1,80p' /tmp/clawsum-backup-smoke.log 2>/dev/null || true
echo "=== find backup scripts / cron ==="
grep -RIn --include='*.sh' --include='*.cron' --include='*.yml' -E 'backup|\.env' /docker/clawsum/scripts 2>/dev/null | grep -iE 'backup|\.env' | sed -n '1,40p' || true
ls /docker/clawsum/scripts/*backup* 2>/dev/null || true
crontab -l 2>/dev/null | grep -iE 'backup|clawsum|env' || true
ls /etc/cron.*/* 2>/dev/null | sed -n '1,40p' || true
grep -RIn -E 'clawsum.*backup|backup.*clawsum|/docker/clawsum/\.env' /etc/cron.d /etc/cron.daily /root 2>/dev/null | sed -n '1,30p' || true

echo "=== search backup stores for .env copies (names only) ==="
for d in /var/backups /backup /backups /root/backups /docker/backups /mnt /media /opt/backups; do
  [[ -d "$d" ]] || continue
  echo "DIR $d"
  find "$d" -iname '*clawsum*' -o -iname '*.env*' 2>/dev/null | sed -n '1,40p'
done

echo "=== any tar/gz containing clawsum .env? (filename scan) ==="
find /var/backups /root /docker -maxdepth 4 \( -name '*.tar' -o -name '*.tar.gz' -o -name '*.tgz' -o -name '*.zip' \) 2>/dev/null | sed -n '1,40p'

echo "=== compare: is current OR key identical to CEOroof? ==="
# only if we can reach ceoroof; fingerprint only
python3 <<'PY'
import hashlib, json
from pathlib import Path
k=json.loads(Path('/docker/clawsum/secrets/openrouter.json').read_text())['OPENROUTER_API_KEY']
print('clawsum_fp', hashlib.sha256(k.encode()).hexdigest()[:12])
PY
