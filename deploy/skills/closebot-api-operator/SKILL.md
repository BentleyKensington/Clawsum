---
name: closebot-api-operator
description: Operate CloseBot agency via REST (X-CB-KEY). List bots, sources, leads, metrics. Send/publish/billing = Tier 2.
agents: [closebot, ghl, admin]
cells: [wnn-client]
tier_autonomous: 1
credentials: [CLOSEBOT_API_KEY]
approval_actions: [customer_comms, billing_charge, bot_publish]
---

# CloseBot API operator

Docs: https://developers.closebot.com/ · Base `https://api.closebot.com` · Header `X-CB-KEY`.

Key UI: https://app.closebot.com/settings?tab=keys  
VPS: `CLOSEBOT_API_KEY` in `/docker/clawsum/.env` (compose already passes it into the gateway).

Paperclip **cannot** sync this skill. Install:

```bash
bash /docker/clawsum/scripts/install-openclaw-skill.sh closebot-api-operator
```

## When to use

Agency health, bot list, lead search, source config review, metrics. Not GHL PIT work (that is `ghl`).

## Instructions

```bash
python3 /docker/clawsum/skills/closebot-api-operator/scripts/closebot_request.py GET /agency/current
python3 /docker/clawsum/skills/closebot-api-operator/scripts/closebot_request.py GET /agency/source
python3 /docker/clawsum/skills/closebot-api-operator/scripts/closebot_request.py GET /bot
```

1. Confirm key exists without printing it (`printenv` length only).
2. GET is Tier 0–1. Summarize in Obsidian `CloseBot/` — no PII dumps in Discord.
3. Search leads when Boss names a person/phone.
4. **Tier 2:** `POST` message to lead, publish/save bot, wallet refill, delete source/bot, billing updates.
5. CRM-specific source install may require OAuth in the CloseBot UI — say so; don’t fake it.

## Escalation

401 → Boss re-issue key. Send to a live lead without approval → refuse.
