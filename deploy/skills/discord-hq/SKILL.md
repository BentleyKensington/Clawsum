# Discord HQ — preferred mobile ops channel

## When to use

- Boss wants phone alerts / digests on Discord (dual-write with Telegram until verified).
- Provision or re-sync HQ layout (roles, categories, channels, forum tags).
- Enable OpenClaw 2-way Discord bindings (one agent per channel).

## Credentials

`DISCORD_*` — see [DISCORD-HQ.md](../../docs/DISCORD-HQ.md). Never paste tokens into chat.

## Commands

```bash
# After Boss puts DISCORD_BOT_TOKEN + DISCORD_GUILD_ID in .env:
python3 /docker/clawsum/scripts/discord-provision-hq.py
python3 /docker/clawsum/scripts/enable-discord.py
python3 /docker/clawsum/scripts/apply-discord-bindings.py
cd /docker/clawsum && docker compose restart openclaw-gateway
bash /docker/clawsum/scripts/discord-smoke-test.sh

# Manual notify:
python3 /docker/clawsum/scripts/clawsum_notify.py "test alert"
python3 /docker/clawsum/scripts/clawsum_notify.py --digest "test digest"
```

## Risk

Tier 1 for notify / provision. Changing OpenClaw bindings = Tier 2 (coding/admin supervised).

## Rules

- No secrets in Discord.
- Approvals stay in Boss UI; Discord only links.
- `NOTIFY_CHANNELS=discord,telegram` until Boss verifies.
