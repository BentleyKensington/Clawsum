---
name: rocco-ops-sentry
description: Watch Clawsum health — gateway, channels, Paperclip proxy, Grafana, stuck agents, LLM spend. Notify Boss with a recommended fix. No exploits.
agents: [rocco, pentest, admin, coding]
cells: [clawsum-platform]
tier_autonomous: 1
credentials: [POSTGRES_*, GRAFANA_*, DISCORD_*, TELEGRAM_*, OPENCLAW_*]
approval_actions: []
---

# Rocco ops sentry

See [ROCCO-SECURE.md](../../docs/ROCCO-SECURE.md).

## When to use

Heartbeat silence, chat down, “is it frozen?”, token burn, Grafana red.

## Instructions

1. Read-only checks (host):

```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | head -40
python3 /docker/clawsum/scripts/pentest-surface-scan.py --markdown 2>/dev/null || true
```

2. Confirm Discord/Telegram plugins enabled in `openclaw.json` (do not force-disable).
3. Paperclip: agents must use `:3102`, not public Authelia URL.
4. If chat was down: `chat-outage-watch.py` / replay docs.
5. Notify via existing `pentest-notify` / Discord alerts — **no secrets**.
6. Open a Coding/Admin Paperclip issue with the recommended command list. Do not apply.

## Escalation

Active credential leak → notify immediately, redacted. Rotate = Tier 3 human. Offensive pentest requests → refuse.
