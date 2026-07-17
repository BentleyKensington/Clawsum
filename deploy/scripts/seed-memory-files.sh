#!/bin/bash
# Create daily memory stubs so session startup reads do not fail.
set -eo pipefail
BASE=/docker/clawsum/data/.openclaw
TODAY=${TODAY:-$(TZ=America/Chicago date +%Y-%m-%d)}
YDAY=$(TZ=America/Chicago date -d yesterday +%Y-%m-%d 2>/dev/null || TZ=America/Chicago date -v-1d +%Y-%m-%d 2>/dev/null || echo "")

AGENTS=(admin coding data realestate ghl comms research planning paperclip)

stub() {
  local agent=$1 date=$2
  cat >"$dir/memory/${date}.md" <<EOF
# ${date} — ${agent}

- Clawsum multi-agent workspace initialized.
- Telegram group bound; use @YourTelegramBot for requests in this domain.
EOF
}

for agent in "${AGENTS[@]}"; do
  dir="$BASE/workspace-${agent}"
  mkdir -p "$dir/memory"
  # AGENTS.md boot reads today + yesterday; missing yesterday causes post-pong errors.
  for d in "$TODAY" "$YDAY" "2026-05-21" "2026-05-20" "2026-05-22"; do
    [[ -z "$d" ]] && continue
    f="$dir/memory/${d}.md"
    if [[ ! -f "$f" ]]; then
      stub "$agent" "$d"
      echo "created $f"
    fi
  done
  chown -R 1000:1000 "$dir/memory"
done

# Preserve rich admin history if present
ADMIN_MEM="$BASE/workspace-admin/memory/2026-05-21.md"
if [[ -f "$ADMIN_MEM" ]] && [[ $(wc -l <"$ADMIN_MEM") -gt 5 ]]; then
  echo "kept existing admin 2026-05-21.md"
fi

echo "Done."
