#!/usr/bin/env bash
# Discord HQ smoke: dual-write notify + config sanity
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
cd "$ROOT"

echo "== Discord env =="
python3 - <<'PY'
from pathlib import Path

env = {}
for line in Path("/docker/clawsum/.env").read_text(encoding="utf-8", errors="replace").splitlines():
    raw = line.strip()
    if not raw or raw.startswith("#") or "=" not in raw:
        continue
    k, _, v = raw.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")

required = ("DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID")
missing = [k for k in required if not env.get(k)]
print(f"guild={env.get('DISCORD_GUILD_ID', 'unset')}")
print(f"alert_channel={env.get('DISCORD_ALERT_CHANNEL_ID', 'unset')}")
print(f"digest_channel={env.get('DISCORD_DIGEST_CHANNEL_ID', 'unset')}")
print(f"NOTIFY_CHANNELS={env.get('NOTIFY_CHANNELS', 'discord,telegram')}")
if missing:
    raise SystemExit("missing: " + ", ".join(missing))
PY

echo "== Map file =="
if [[ -f data/discord-hq-map.json ]]; then
  python3 -c "import json; d=json.load(open('data/discord-hq-map.json')); print('channels', len(d.get('channels',{}))); print('roles', list((d.get('roles') or {}).keys()))"
else
  echo "WARN: data/discord-hq-map.json missing"
fi

echo "== OpenClaw discord plugin =="
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/docker/clawsum/data/.openclaw/openclaw.json")
if not p.exists():
    print("openclaw.json missing"); raise SystemExit(1)
c = json.loads(p.read_text())
allow = (c.get("plugins") or {}).get("allow") or []
ent = ((c.get("plugins") or {}).get("entries") or {}).get("discord") or {}
ch = (c.get("channels") or {}).get("discord") or {}
print("allow_has_discord", "discord" in allow)
print("plugin_enabled", ent.get("enabled"))
print("channel_enabled", ch.get("enabled"))
binds = [b for b in (c.get("bindings") or []) if (b.get("match") or {}).get("channel") == "discord"]
print("discord_bindings", len(binds))
PY

echo "== Dual-write smoke =="
python3 scripts/clawsum_notify.py "Clawsum Discord smoke — boss-alerts dual-write OK"
python3 scripts/clawsum_notify.py --digest "Clawsum Discord smoke — ops-digest dual-write OK"

echo "OK — check Discord #boss-alerts / #ops-digest and Telegram"
