#!/usr/bin/env bash
# Seed shared Clawsum company pack into OpenClaw agent workspaces + Hermes home.
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SRC="${ROOT}/personas/clawsum"
BASE="${ROOT}/data/.openclaw"
HERMES_DST="${ROOT}/paperclip-data/.hermes/company-pack"
CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"

if [[ ! -d "$SRC" ]]; then
  echo "missing $SRC" >&2
  exit 1
fi

FILES=(COMPANY.md VALUES.md APPROVALS.md COMMUNICATION.md MEMORY_POLICY.md DECISIONS.md ESCALATION.md SECURITY.md USER.md)

seed_dir() {
  local dir="$1"
  mkdir -p "$dir/company"
  for f in "${FILES[@]}"; do
    cp -f "$SRC/$f" "$dir/company/$f"
  done
}

echo "== seed OpenClaw workspaces =="
for agent in admin coding data realestate ghl comms research planning paperclip hermes; do
  dir="$BASE/workspace-${agent}"
  if [[ -d "$dir" ]] || [[ -d "$BASE" ]]; then
    mkdir -p "$dir"
    seed_dir "$dir"
    # Pointer file agents can open first
    cat > "$dir/COMPANY_PACK.md" <<EOF
# Company pack

Shared Clawsum policy lives in \`company/\`.
Read \`company/COMPANY.md\` and \`company/APPROVALS.md\` on session start (after SOUL).
Cell overlays may narrow scope; they must not weaken approvals or security.
EOF
    chown -R 1000:1000 "$dir/company" "$dir/COMPANY_PACK.md" 2>/dev/null || true
    echo "seeded workspace-${agent}"
  fi
done

echo "== seed Hermes company pack =="
mkdir -p "$HERMES_DST"
for f in "${FILES[@]}"; do
  cp -f "$SRC/$f" "$HERMES_DST/$f"
done

# Also copy into running Paperclip Hermes home if container exists
if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  docker exec -u root "$CONTAINER" mkdir -p /paperclip/.hermes/company-pack
  docker cp "$HERMES_DST/." "${CONTAINER}:/paperclip/.hermes/company-pack/"
  echo "copied into $CONTAINER:/paperclip/.hermes/company-pack"
fi

echo DONE
