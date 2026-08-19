#!/usr/bin/env bash
# Run memory-dream.py inside paperclip venv; sync Obsidian notes back to vault.
#
# Ubuntu cron on this host ignores CRON_TZ (schedules as UTC). Hourly is fine
# every clock hour; nightly/weekly are Chicago-gated + once-per-period markers.
set -eo pipefail
STAGE="${1:?usage: run-memory-dream.sh hourly|nightly|weekly [extra args...]}"
shift || true
ROOT=/docker/clawsum
C=clawsum-paperclip-1
DREAM_ROOT=/paperclip/dream-root
export TZ=America/Chicago
MARKER_DIR="$ROOT/data/reports"
mkdir -p "$MARKER_DIR"

H=$(date +%-H)
M=$(date +%-M)
DOW=$(date +%u)   # 1=Mon … 7=Sun
STAMP=$(date +%Y-%m-%d)
WEEK=$(date +%G-W%V)

case "$STAGE" in
  nightly)
    # Window: 02:15–02:19 Chicago (cron fires every hour at :15)
    if [ "$H" -ne 2 ] || [ "$M" -lt 15 ] || [ "$M" -gt 19 ]; then
      exit 0
    fi
    MARKER="$MARKER_DIR/.dream-nightly-$STAMP"
    if [ -f "$MARKER" ]; then
      echo "$(date -Is) skip nightly: already ran $STAMP" >> "$MARKER_DIR/memory-dream-nightly.log"
      exit 0
    fi
    ;;
  weekly)
    # Window: Sunday 03:30–03:34 Chicago (cron fires every hour at :30)
    if [ "$DOW" -ne 7 ] || [ "$H" -ne 3 ] || [ "$M" -lt 30 ] || [ "$M" -gt 34 ]; then
      exit 0
    fi
    MARKER="$MARKER_DIR/.dream-weekly-$WEEK"
    if [ -f "$MARKER" ]; then
      echo "$(date -Is) skip weekly: already ran $WEEK" >> "$MARKER_DIR/memory-dream-weekly.log"
      exit 0
    fi
    ;;
esac

mkdir -p "$ROOT/paperclip-data/clawsum-scripts" \
         "$ROOT/paperclip-data/dream-root/obsidian/Admin/Memory" \
         "$ROOT/data/reports" \
         "$ROOT/obsidian/Admin/Memory"
cp -f "$ROOT/scripts/memory-dream.py" \
      "$ROOT/scripts/memory-fact-extract.py" \
      "$ROOT/scripts/clawsum_arcade.py" \
      "$ROOT/paperclip-data/clawsum-scripts/"
sed -i 's/\r$//' "$ROOT/paperclip-data/clawsum-scripts/"*.py

env_get() {
  local k="$1"
  grep -E "^${k}=" "$ROOT/.env" 2>/dev/null | head -1 | cut -d= -f2- | sed 's/\r$//; s/^"//; s/"$//' || true
}

ENVF="$ROOT/paperclip-data/clawsum-scripts/.dream.env"
umask 077
{
  echo "POSTGRES_HOST=127.0.0.1"
  echo "POSTGRES_PORT=5432"
  echo "POSTGRES_USER=clawsum"
  echo "POSTGRES_PASSWORD=$(env_get POSTGRES_PASSWORD)"
  echo "POSTGRES_DB=clawsum"
  echo "OPENAI_API_KEY=$(env_get OPENAI_API_KEY)"
  echo "OPENROUTER_API_KEY=$(env_get OPENROUTER_API_KEY)"
  echo "ARCADEDB_URL=$(env_get ARCADEDB_URL)"
  echo "ARCADEDB_DATABASE=$(env_get ARCADEDB_DATABASE)"
  echo "ARCADEDB_USER=root"
  echo "ARCADEDB_ROOT_PASSWORD=$(env_get ARCADEDB_ROOT_PASSWORD)"
  echo "CLAWSUM_SOURCE_HOST=vps"
  echo "CLAWSUM_ROOT=${DREAM_ROOT}"
  echo "MEMORY_EXTRACT_MODEL=$(env_get MEMORY_EXTRACT_MODEL)"
  echo "MEMORY_DREAM_MODEL=$(env_get MEMORY_DREAM_MODEL)"
} > "$ENVF"
# defaults for empty arcade URL/db
grep -q '^ARCADEDB_URL=.\+' "$ENVF" || sed -i 's|^ARCADEDB_URL=$|ARCADEDB_URL=http://127.0.0.1:2480|' "$ENVF"
grep -q '^ARCADEDB_DATABASE=.\+' "$ENVF" || sed -i 's|^ARCADEDB_DATABASE=$|ARCADEDB_DATABASE=clawsum_graph|' "$ENVF"

# Quote extra args safely for remote bash
EXTRA_Q=""
for a in "$@"; do
  EXTRA_Q+=" $(printf '%q' "$a")"
done

docker exec -u root "$C" bash -lc "
set -a
. /paperclip/clawsum-scripts/.dream.env
set +a
export PATH=/paperclip/.hermes-venv/bin:\$PATH
export CLAWSUM_ROOT=${DREAM_ROOT}
mkdir -p ${DREAM_ROOT}/obsidian/Admin/Memory
cd /paperclip/clawsum-scripts
python3 -u memory-dream.py --stage $(printf '%q' "$STAGE") ${EXTRA_Q}
"
RC=$?

# Sync dream artifacts into real Obsidian vault
if [ -d "$ROOT/paperclip-data/dream-root/obsidian/Admin/Memory" ]; then
  cp -f "$ROOT/paperclip-data/dream-root/obsidian/Admin/Memory/"*.md \
    "$ROOT/obsidian/Admin/Memory/" 2>/dev/null || true
fi
for f in Latest-Dream.md Self-Model.md; do
  if [ -f "$ROOT/paperclip-data/dream-root/obsidian/Admin/$f" ]; then
    cp -f "$ROOT/paperclip-data/dream-root/obsidian/Admin/$f" "$ROOT/obsidian/Admin/$f"
  fi
done
chown -R 1000:1000 "$ROOT/obsidian/Admin/Memory" \
  "$ROOT/obsidian/Admin/Latest-Dream.md" \
  "$ROOT/obsidian/Admin/Self-Model.md" 2>/dev/null || true

if [ "$RC" -eq 0 ]; then
  case "$STAGE" in
    nightly) touch "$MARKER_DIR/.dream-nightly-$STAMP" ;;
    weekly)  touch "$MARKER_DIR/.dream-weekly-$WEEK" ;;
  esac
fi

exit $RC
