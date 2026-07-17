#!/bin/bash
docker run --rm --network container:clawsum-openclaw-gateway-1 \
  -v /docker/clawsum/data/.openclaw:/home/node/.openclaw \
  -e HOME=/home/node -e OPENCLAW_STATE_DIR=/home/node/.openclaw \
  -e OPENCLAW_CONFIG_PATH=/home/node/.openclaw/openclaw.json \
  ${OPENCLAW_IMAGE:-ghcr.io/openclaw/openclaw:2026.6.10} \
  node dist/index.js devices approve --help 2>&1 | head -40
