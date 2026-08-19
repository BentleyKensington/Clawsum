#!/usr/bin/env bash
set -euo pipefail
echo "=== proxy ==="
systemctl is-active clawsum-paperclip-agent-proxy || true
curl -sS -m 3 http://127.0.0.1:3100/api/health | head -c 160; echo
curl -sS -m 3 http://127.0.0.1:3102/api/health | head -c 160; echo
echo "=== gateway ==="
docker exec clawsum-openclaw-gateway-1 printenv PAPERCLIP_API_URL || true
docker exec clawsum-openclaw-gateway-1 sh -c 'curl -sS -m 5 -w "\n%{http_code}\n" http://host.docker.internal:3102/api/health' | tail -5
echo "=== tools ==="
command -v ffmpeg || true
command -v ffprobe || true
command -v yt-dlp || true
ffmpeg -version 2>/dev/null | head -1 || true
yt-dlp --version 2>/dev/null || true
echo "=== minio ==="
docker ps --filter name=minio --format '{{.Names}} {{.Status}}' || true
echo "=== env prefixes present ==="
grep -E '^(MINIO_|FFMPEG|WHISPER|PAPERCLIP_AGENT|PAPERCLIP_API|PAPERCLIP_COMPANY)' /docker/clawsum/.env \
  | sed -E 's/=.*/=SET/' || true
echo "=== media agent ==="
python3 - <<'PY'
import json
from pathlib import Path
cfg=json.loads(Path('/docker/clawsum/data/.openclaw/openclaw.json').read_text())
ids=[a.get('id') for a in cfg.get('agents',{}).get('list',[])]
print('media_in_openclaw', 'media' in ids)
print('workspace_media', Path('/docker/clawsum/data/.openclaw/workspace-media').exists())
PY
