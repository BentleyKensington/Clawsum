#!/usr/bin/env bash
set +u
set -eo pipefail
echo "=== errors.log ==="
docker exec clawsum-paperclip-1 tail -n 80 /paperclip/.hermes/logs/errors.log
echo "=== agent.log ==="
docker exec clawsum-paperclip-1 tail -n 60 /paperclip/.hermes/logs/agent.log
echo "=== how to start gateway ==="
docker exec clawsum-paperclip-1 bash -lc 'export PATH=/paperclip/.hermes-venv/bin:$PATH; hermes --help 2>&1 | head -60; echo ---; hermes gateway --help 2>&1 | head -40; which hermes'
echo "=== hermes-dashboard.sh ==="
head -80 /docker/clawsum/scripts/hermes-dashboard.sh
echo "=== gateway scripts ==="
ls /docker/clawsum/scripts/*gateway* /docker/clawsum/scripts/*hermes* 2>/dev/null | head -40
