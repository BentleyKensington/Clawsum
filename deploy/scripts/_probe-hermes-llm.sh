#!/usr/bin/env bash
set -euo pipefail
echo "=== hermes home files ==="
ls -la /docker/clawsum/paperclip-data/.hermes/ | head -40
echo "=== config/model search ==="
find /docker/clawsum/paperclip-data/.hermes -maxdepth 3 -type f \( -name '*.yaml' -o -name '*.yml' -o -name '*.json' -o -name '.env*' -o -name '*.toml' \) 2>/dev/null | head -50
echo "=== grep model/openrouter in hermes home ==="
grep -RIn --include='*.yaml' --include='*.yml' --include='*.json' --include='*.env*' --include='*.toml' -E 'openrouter|openai|anthropic|model|provider|base_url' /docker/clawsum/paperclip-data/.hermes 2>/dev/null | grep -viE 'key|token|secret|password' | head -60
echo "=== container env keys ==="
docker exec clawsum-paperclip-1 env | grep -iE 'OPENROUTER|OPENAI|ANTHROPIC|MODEL|HERMES|LLM' | cut -d= -f1 || true
echo "=== recent chat/api errors ==="
docker exec clawsum-paperclip-1 bash -lc 'grep -iE "429|rate limit|unavailable|openrouter|error" /paperclip/logs/hermes-dashboard.log 2>/dev/null | tail -30' || true
find /docker/clawsum/paperclip-data -name '*.log' 2>/dev/null | head -20
