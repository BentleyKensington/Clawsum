#!/bin/bash
set -euo pipefail
python3 <<'PY'
from pathlib import Path
env = {}
for line in Path("/docker/clawsum/.env").read_text(encoding="utf-8", errors="replace").splitlines():
    raw = line.strip()
    if not raw or raw.startswith("#") or "=" not in raw:
        continue
    k, _, v = raw.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")
t = env.get("DISCORD_BOT_TOKEN", "")
print("TOKEN", f"set len={len(t)}" if t else "MISSING")
print("GUILD", env.get("DISCORD_GUILD_ID") or "MISSING")
print("USER", env.get("DISCORD_BOSS_USER_ID") or "MISSING")
print("NOTIFY", env.get("NOTIFY_CHANNELS") or "MISSING")
missing = [k for k in ("DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID", "DISCORD_BOSS_USER_ID") if not env.get(k)]
raise SystemExit(1 if missing else 0)
PY
