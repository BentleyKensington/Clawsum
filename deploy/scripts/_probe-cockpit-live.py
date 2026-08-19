#!/usr/bin/env python3
import json
from pathlib import Path

auth = json.loads(
    Path(
        "/docker/clawsum/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/authority.json"
    ).read_text()
)
print("authority agents", len(auth.get("agents") or []), "skills", len(auth.get("skills") or []))
print("agent_ids", [a.get("id") for a in auth.get("agents") or []])

oc = Path("/docker/clawsum/data/.openclaw/openclaw.json")
if oc.is_file():
    cfg = json.loads(oc.read_text())
    ch = cfg.get("channels") or {}
    for name in ("discord", "telegram", "whatsapp"):
        row = ch.get(name) or {}
        print("channel", name, "enabled=", row.get("enabled"))
else:
    print("openclaw.json missing")

live = Path("/docker/clawsum/data/reports/cron-live.txt")
print("cron-live exists", live.is_file(), "lines", len(live.read_text().splitlines()) if live.is_file() else 0)
if live.is_file():
    for line in live.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "CRON_TZ" not in line:
            print(" ", line[:120])

briefs = Path("/docker/clawsum/data/reports/agent-daily-briefs.json")
if briefs.is_file():
    d = json.loads(briefs.read_text())
    print("briefs", len(d.get("briefs") or []), "alerts", d.get("hermes_alerts"))
