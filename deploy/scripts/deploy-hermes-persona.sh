#!/usr/bin/env bash
# Deploy Hermes CEO persona files (SOUL, BOOT, MEMORY, LAST_SESSION, …) into Hermes home.
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SRC="${HERMES_PERSONA_SRC:-${ROOT}/examples/hermes-cockpit}"
CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
H=/paperclip/.hermes
HOST_H="${ROOT}/paperclip-data/.hermes"

FILES=(SOUL.md BOOT.md USER.md MEMORY.md LAST_SESSION.md WORKFLOWS.md APPROVALS.md)

mkdir -p "$HOST_H"
for f in "${FILES[@]}"; do
  if [[ -f "$SRC/$f" ]]; then
    cp -f "$SRC/$f" "$HOST_H/$f"
    echo "host $f"
  fi
done

# Skin welcome
if [[ -f "$SRC/skins/clawsum.yaml" ]]; then
  mkdir -p "$HOST_H/skins"
  cp -f "$SRC/skins/clawsum.yaml" "$HOST_H/skins/clawsum.yaml"
fi

if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  for f in "${FILES[@]}"; do
    if [[ -f "$HOST_H/$f" ]]; then
      docker cp "$HOST_H/$f" "${CONTAINER}:${H}/$f"
    fi
  done
  if [[ -f "$HOST_H/skins/clawsum.yaml" ]]; then
    docker exec -u root "$CONTAINER" mkdir -p "${H}/skins"
    docker cp "$HOST_H/skins/clawsum.yaml" "${CONTAINER}:${H}/skins/clawsum.yaml"
  fi
  # Prefer SOUL in Hermes profile/workspace if present
  docker exec -u root "$CONTAINER" bash -lc "
    for d in ${H}/profiles/* ${H}/workspace ${H}; do
      [[ -d \$d ]] || continue
      for f in SOUL.md BOOT.md USER.md MEMORY.md LAST_SESSION.md WORKFLOWS.md APPROVALS.md; do
        [[ -f ${H}/\$f ]] && cp -f ${H}/\$f \$d/\$f 2>/dev/null || true
      done
    done
    echo persona synced under ${H}
  "
fi

echo DONE
