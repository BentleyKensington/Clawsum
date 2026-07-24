#!/usr/bin/env bash
# Ensure TELEGRAM_* chat ids exist for Boss alerts (OAuth, reports, reminders).
set -euo pipefail
ENV_FILE=/docker/clawsum/.env
OC=/docker/clawsum/data/.openclaw/openclaw.json

python3 <<'PY'
import json
from pathlib import Path

env_path = Path("/docker/clawsum/.env")
cfg = json.loads(Path("/docker/clawsum/data/.openclaw/openclaw.json").read_text())

admin_id = ""
for want in ("admin", "paperclip"):
    for b in cfg.get("bindings") or []:
        if b.get("agentId") != want:
            continue
        peer = (b.get("match") or {}).get("peer") or b.get("peer") or {}
        if peer.get("kind") == "group" and peer.get("id"):
            admin_id = str(peer["id"])
            break
    if admin_id:
        break

if not admin_id:
    raise SystemExit("could not resolve admin Telegram group from openclaw bindings")

updates = {
    "TELEGRAM_ADMIN_CHAT_ID": admin_id,
    "TELEGRAM_REPORT_CHAT_ID": admin_id,
}

lines = env_path.read_text().splitlines() if env_path.exists() else []
seen = set()
out = []
for line in lines:
    if "=" in line and not line.strip().startswith("#"):
        k = line.split("=", 1)[0].strip()
        if k in updates:
            out.append(f"{k}={updates[k]}")
            seen.add(k)
            continue
    out.append(line)
for k, v in updates.items():
    if k not in seen:
        out.append(f"{k}={v}")
env_path.write_text("\n".join(out) + "\n")
print(f"Set TELEGRAM_ADMIN_CHAT_ID / TELEGRAM_REPORT_CHAT_ID -> {admin_id}")
PY
