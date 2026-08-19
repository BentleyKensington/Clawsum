#!/usr/bin/env bash
# Do NOT clobber config.yaml. Repair from last known-good snapshot only.
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
python3 "$ROOT/scripts/hermes-config-safe.py" --repair \
  --path "$ROOT/paperclip-data/.hermes/config.yaml"
echo "rewrite refused — use hermes-config-safe.py --repair only"
