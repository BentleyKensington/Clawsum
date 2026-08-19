#!/usr/bin/env bash
set -eu
C=clawsum-paperclip-1
echo "=== live config.yaml ==="
docker exec $C cat /paperclip/.hermes/config.yaml
echo
echo "=== corrupt bak ==="
docker exec $C cat /paperclip/.hermes/config.yaml.corrupt.20260729-180145.bak
echo
echo "=== web_server chat gate ==="
docker exec $C sed -n "2155,2275p" /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py
echo "===== 6225-6260 ====="
docker exec $C sed -n "6225,6265p" /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py
echo "===== 5648-5745 ====="
docker exec $C sed -n "5648,5745p" /paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py
