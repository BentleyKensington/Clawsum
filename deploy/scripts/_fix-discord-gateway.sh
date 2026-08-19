#!/bin/bash
set -euo pipefail
chown -R 1000:1000 /docker/clawsum/data/.openclaw
ls -la /docker/clawsum/data/.openclaw/openclaw.json

python3 - <<'PY'
from pathlib import Path
for line in Path("/docker/clawsum/.env").read_text().splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        v = line.split("=", 1)[1]
        print("raw_len", len(v))
        print("has_dollar", "$" in v)
        print("has_hash", "#" in v)
        print("quoted", v[:1] in "\"'")
        # Docker compose env_file treats $ as variable expansion — quote if needed
        break
PY

# Ensure token is single-quoted in .env so docker compose doesn't eat $ fragments
python3 - <<'PY'
from pathlib import Path
path = Path("/docker/clawsum/.env")
lines = path.read_text().splitlines()
out = []
changed = False
for line in lines:
    if line.startswith("DISCORD_BOT_TOKEN="):
        v = line.split("=", 1)[1].strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            out.append(line)
        else:
            # single-quote for docker-compose env_file; escape existing single quotes
            safe = "'" + v.replace("'", "'\"'\"'") + "'"
            out.append(f"DISCORD_BOT_TOKEN={safe}")
            changed = True
            print("quoted DISCORD_BOT_TOKEN for docker env_file")
    else:
        out.append(line)
if changed:
    path.write_text("\n".join(out) + "\n")
    print("updated .env")
else:
    print("token quoting unchanged")
PY

cd /docker/clawsum
docker compose up -d --force-recreate openclaw-gateway
sleep 12
docker ps --filter name=clawsum-openclaw-gateway --format '{{.Names}} {{.Status}}'
echo "TOKEN_LEN=$(docker exec clawsum-openclaw-gateway-1 printenv DISCORD_BOT_TOKEN | wc -c)"
docker logs clawsum-openclaw-gateway-1 --tail 60 2>&1 | grep -iE 'discord|ready|error|EACCES|listening|Invalid|plugin|telegram' | tail -50
