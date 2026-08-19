#!/usr/bin/env bash
set -eu
C=clawsum-paperclip-1
echo "=== gateway_state.json ==="
docker exec $C cat /paperclip/.hermes/gateway_state.json 2>/dev/null || true
echo
echo "=== gateway.pid leftover ==="
docker exec $C cat /paperclip/.hermes/gateway.pid 2>/dev/null || true
echo
echo "=== corrupt config bak ==="
docker exec $C ls -la /paperclip/.hermes/config.yaml /paperclip/.hermes/config.yaml.corrupt.20260729-180145.bak
echo "=== config.yaml mtime / size ==="
docker exec $C stat -c '%y %s %n' /paperclip/.hermes/config.yaml /paperclip/.hermes/config.yaml.corrupt.20260729-180145.bak /paperclip/.hermes/gateway_state.json /paperclip/logs/hermes-gateway.log
echo "=== platforms dir ==="
docker exec $C ls -la /paperclip/.hermes/platforms 2>/dev/null | sed -n "1,30p"
echo "=== grep config platforms ==="
docker exec $C grep -nE "telegram|discord|platform|gateway" /paperclip/.hermes/config.yaml | sed -n "1,40p"
echo "=== hermes chat vs gateway in package ==="
docker exec $C grep -Rsn --include="*.py" "gateway_running\|active_sessions\|Gateway stopped" /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli 2>/dev/null | sed -n "1,40p"
echo "=== paperclip recreate Aug 5 hint ==="
docker inspect -f '{{.State.StartedAt}} finished={{.State.FinishedAt}}' clawsum-paperclip-1
docker logs --since 2026-08-05T02:59:00 --until 2026-08-05T03:05:00 clawsum-paperclip-1 2>&1 | sed -n "1,15p" || true
