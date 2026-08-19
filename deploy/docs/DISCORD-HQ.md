# Discord HQ — preferred mobile channel (replaces Telegram over time)

Clawsum’s phone surface is **Discord**. Telegram stays on **dual-write** until you verify Discord is solid, then flip `NOTIFY_CHANNELS=discord`.

Browser remains system of record: Hermes / Paperclip / Grafana. Approvals stay in Boss UI (Discord posts links only).

---

## Can Cursor / Auto set up Discord via API?

**Yes — through a Discord Bot you create**, not by logging in as you.

There is **no Discord MCP** in this Cursor workspace. What works:

1. You create a Discord Application + Bot and invite it to your server.
2. You put `DISCORD_BOT_TOKEN` + `DISCORD_GUILD_ID` in `/docker/clawsum/.env`.
3. Auto (or you) runs `discord-provision-hq.py` — creates roles, categories, channels, forum tags via Discord REST API.
4. Then `enable-discord.py` + `apply-discord-bindings.py` wire OpenClaw **2-way** chat.

Paste the token in chat only if you accept rotating it afterward; prefer editing `.env` on the VPS yourself:

```bash
ssh root@76.13.97.82
nano /docker/clawsum/.env
```

---

## Cutting-edge layout we use (2026 patterns)

Research consensus: **8–20 channels**, categories by job, **least privilege**, forums for threaded work, voice for standups, role hierarchy with bot **below** Admin but **above** roles it manages.

| Pattern | Clawsum use |
|---------|-------------|
| Categories | START / BOSS / OPS / AGENTS / WORK / VOICE / STAFF |
| Text channels | Ongoing topics (`#boss-alerts`, `#ops-digest`) |
| Forum channel | `#tasks` with tags: urgent, blocked, needs-boss, done, watch |
| Threads | Temporary digressions inside forums / agent channels |
| Roles | Boss, Ops, Agent, Verified (+ Owner) |
| One-bot-per-channel | OpenClaw binding: each `#agent-*` → one agentId |
| Free-respond | Boss desk + agent channels (`requireMention: false`) |
| Mentions elsewhere | Alerts/digest channels stay quieter |
| Hashtags | Discord has **no** Twitter hashtags — use **forum tags** + channel topics |

### Provisioned channels

```text
📋 START HERE     #start-here  #rules
🚨 BOSS           #boss-alerts  #boss-desk  #approvals
📊 OPS            #ops-digest  #gmail-inbox  #monitoring
🤖 AGENTS         #jarvis-hermes #admin #paperclip #coding #data #ghl #comms #research
🗂 WORK           #tasks (forum)  #wins
🔊 VOICE          Boss Standup · Ops Lounge · AFK
🛡 STAFF          #bot-test  #mod-log
```

---

## Boss setup checklist (you)

1. [Discord Developer Portal](https://discord.com/developers/applications) → **New Application** → **Bot**
2. Copy **Bot Token**
3. Privileged intents: **Message Content Intent**, **Server Members Intent**
4. OAuth2 → URL Generator → scopes `bot` → permissions:
   - Manage Channels, Manage Roles, Send Messages, Embed Links, Read Message History,
     View Channels, Create Public Threads, Connect, Speak (optional)
5. Open invite URL → pick / create **Clawsum HQ** server
6. Discord app → User Settings → Advanced → **Developer Mode ON**
7. Right-click server → **Copy Server ID**
8. Right-click your avatar → **Copy User ID** (for DM allowlist)

On VPS `.env`:

```env
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...
DISCORD_BOSS_USER_ID=...
NOTIFY_CHANNELS=discord,telegram
```

Then:

```bash
python3 /docker/clawsum/scripts/discord-provision-hq.py
python3 /docker/clawsum/scripts/enable-discord.py
python3 /docker/clawsum/scripts/apply-discord-bindings.py
cd /docker/clawsum && docker compose restart openclaw-gateway
bash /docker/clawsum/scripts/discord-smoke-test.sh
```

Drag the **bot’s role** above Boss/Ops/Verified in Server Settings → Roles so it can assign those roles later.

---

## Dual-write → Discord-only

| Phase | `NOTIFY_CHANNELS` |
|-------|-------------------|
| Now | `discord,telegram` |
| After ~1–2 weeks verified | `discord` |
| Emergency fallback | `telegram` |

Scripts using `clawsum_notify.py`: Gmail OAuth alerts, daily global report, reminders, Grafana notifier.

---

## 2-way chat

OpenClaw Discord plugin (bundled) + bindings from `apply-discord-bindings.py`.

Message `#boss-desk` or `#jarvis-hermes` as Boss — agent replies in-channel. Do **not** paste secrets.

---

## Scripts

| Script | Role |
|--------|------|
| `discord-provision-hq.py` | API create roles/channels → `.env` + `data/discord-hq-map.json` |
| `enable-discord.py` | Flip OpenClaw `channels.discord` + plugins |
| `apply-discord-bindings.py` | Agent ↔ channel bindings |
| `clawsum_notify.py` | Dual-write send |
| `discord-smoke-test.sh` | End-to-end smoke |

---

## Security

Same as Telegram (`AUTHORITY.md`): no tokens, no raw email bodies, no PIT keys in channels.
