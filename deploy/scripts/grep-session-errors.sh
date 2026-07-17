#!/usr/bin/env bash
set -eu
for a in data ghl comms planning coding admin; do
  echo "=== $a ==="
  f=$(ls -t "/docker/clawsum/data/.openclaw/agents/${a}/sessions/"*.jsonl 2>/dev/null | grep -v trajectory | head -1 || true)
  [[ -z "$f" ]] && echo "  no sessions" && continue
  echo "  $f"
  grep -E 'isError.:true|api.key|Missing|auth|rate.limit|went wrong' "$f" 2>/dev/null | tail -5 || echo "  no errors in log"
done
