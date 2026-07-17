#!/bin/sh
set -eu
exec node dist/index.js devices approve "$1" --url ws://127.0.0.1:18789 --token "$OPENCLAW_GATEWAY_TOKEN"
