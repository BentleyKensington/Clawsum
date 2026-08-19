#!/usr/bin/env bash
# Media Phase 0 on VPS: install CLI tools, MinIO bucket, sample inbox, dry-run ingest.
# Local Boss GPU / Ollama stack is DEFERRED per Boss.
set -euo pipefail
ROOT=/docker/clawsum
cd "$ROOT"

echo "=== Install ffmpeg + yt-dlp if missing ==="
if ! command -v ffmpeg >/dev/null 2>&1; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg
fi
if ! command -v yt-dlp >/dev/null 2>&1; then
  curl -fsSL -o /usr/local/bin/yt-dlp https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp
  chmod a+rx /usr/local/bin/yt-dlp
fi
ffmpeg -version | head -1
yt-dlp --version
ffprobe -version | head -1

echo "=== Ensure media-ingest.py ==="
install -m 0755 -D /tmp/media-ingest.py "$ROOT/scripts/media-ingest.py" 2>/dev/null || true
[ -f "$ROOT/scripts/media-ingest.py" ] || true
sed -i 's/\r$//' "$ROOT/scripts/media-ingest.py" 2>/dev/null || true

echo "=== Media inbox dirs ==="
mkdir -p /docker/clawsum/data/media/inbox /docker/clawsum/data/media/exports
chown -R 1000:1000 /docker/clawsum/data/media 2>/dev/null || true

echo "=== Env prefixes for Media (no secrets printed) ==="
ENVF="$ROOT/.env"
grep -q '^FFMPEG_BIN=' "$ENVF" || echo "FFMPEG_BIN=$(command -v ffmpeg)" >> "$ENVF"
grep -q '^FFPROBE_BIN=' "$ENVF" || echo "FFPROBE_BIN=$(command -v ffprobe)" >> "$ENVF"
grep -q '^YTDLP_BIN=' "$ENVF" || echo "YTDLP_BIN=$(command -v yt-dlp)" >> "$ENVF"
grep -q '^MEDIA_INBOX=' "$ENVF" || echo "MEDIA_INBOX=/docker/clawsum/data/media/inbox" >> "$ENVF"
grep -q '^MEDIA_EXPORTS=' "$ENVF" || echo "MEDIA_EXPORTS=/docker/clawsum/data/media/exports" >> "$ENVF"
# Placeholders if missing — Boss fills real MinIO/Whisper later (local stack deferred)
grep -q '^WHISPER_URL=' "$ENVF" || echo "WHISPER_URL=" >> "$ENVF"
grep -E '^(FFMPEG_BIN|FFPROBE_BIN|YTDLP_BIN|MEDIA_INBOX|MEDIA_EXPORTS|WHISPER_URL|MINIO_)' "$ENVF" | sed -E 's/=.*/=SET/'

echo "=== MinIO bucket clawsum-media (best effort) ==="
if docker ps --format '{{.Names}}' | grep -q minio; then
  # Prefer mc if available
  if command -v mc >/dev/null 2>&1; then
    echo "mc present — create bucket if creds configured"
  else
    echo "minio container up; bucket create deferred to mc/credentials"
  fi
else
  echo "No minio container — blobs stay on disk inbox until MinIO wired"
fi

echo "=== Dry-run ingest ==="
python3 "$ROOT/scripts/media-ingest.py" --watch /docker/clawsum/data/media/inbox --dry-run || true

echo "=== Paperclip Media Phase 0 issue ==="
python3 /tmp/create-media-phase0-issue.py

echo "MEDIA_PHASE0_READY"
