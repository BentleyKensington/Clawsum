# Clawsum skill authority model

Skills do not grant power by themselves. **Paperclip + cell policy + credentials** do.  
This file is the map for who may run what, with which secrets, at which risk tier.

---

## Risk tiers (locked)

| Tier | Meaning | Skill may auto-complete? |
|------|---------|---------------------------|
| **0** | Read-only / summarize / classify | Yes |
| **1** | Drafts, local DB writes, create Paperclip todo | Yes (notify Boss optional) |
| **2** | Client-facing send, prod change, paid spend | **No** — `ops.approvals` + Gerald |
| **3** | Banking, legal, wipe, credential rotate | **Never autonomous** — human only |

Heartbeats remain off until CLA-41 + [RESUME-POLICY.md](../docs/RESUME-POLICY.md).

---

## Agents (assignees)

| Agent | OpenClaw id | Default cells | Typical skill domains |
|-------|-------------|---------------|------------------------|
| **Clawsum Admin** | `admin` | `clawsum-platform`, `personal-admin` | Brief, inbox, approvals liaison, reminders |
| **Clawsum Hermes** | `hermes` | platform (opt-in long runs) | Proactive drive, archive questions — **Boss authorized only** |
| **Clawsum Paperclip** | `paperclip` | platform | Task routing, board hygiene |
| **Clawsum Coding** | `coding` | `hardware-local-ai`, `vocalitic`, platform deploy | VPS, cockpit, OpenClaw config |
| **Clawsum Data** | `data` | platform + analytics cells | Postgres reports, ETL, ArcadeDB |
| **Clawsum GHL** (+ instance overlays) | `ghl` / `ghl-*` | `wnn-client` (+ MCO/AVE/WNN) | CRM, re-engage, pipelines |
| **Clawsum RE** | `realestate` | `real-estate`, `roofing-os` | Deals, storm/roofing intel |
| **Clawsum Comms** | `comms` | `acceptai-fastbuy`, drafts | Outbound drafts (send = Tier 2) |
| **Clawsum Research** | `research` | any (read) | Competitive / brief research |
| **Clawsum Planning** | `planning` | `techtasia`, platform roadmap | Priorities, cell planning |

**Hermes UI** (Nous dashboard) is a *face*, not a credential vault. It proposes; Paperclip assigns; OpenClaw executes.

---

## Credential classes

Never commit values. Skills list **prefixes only**.

| Class | Env / vault | Who may use | Notes |
|-------|-------------|-------------|-------|
| **Gmail readonly** | `GMAIL_CLIENT_*`, `GMAIL_REFRESH_TOKEN`, `GMAIL_ADMIN_ADDRESS` | admin, data (sync scripts) | Sync/review Tier 0–1 |
| **Gmail send** | separate OAuth scope / gog send | admin, comms | **Tier 2 always** |
| **Gog keyring** | `GOG_*` | openclaw gateway | Control UI Gmail tools |
| **Postgres** | `POSTGRES_*` | admin, data, coding (migrate) | ops schema; no public expose |
| **Paperclip API** | `PAPERCLIP_API`, `PAPERCLIP_COMPANY_ID`, JWT | admin, paperclip, hermes (task create) | Board truth |
| **GHL PIT** | `GHL_*_PIT` / per-slug | **ghl cell agent only** | Never share across cells |
| **Telegram** | `TELEGRAM_*` | admin (reports), cell bots | No secrets in group chat |
| **OpenClaw gateway** | `OPENCLAW_*` | coding, admin | Config changes Tier 2 |
| **LLM API** | `OPENAI_*`, `OPENROUTER_*` | triage cron, research | Prefer Codex OAuth for agents |
| **Traefik / ops auth** | `BOSS_OPS_*`, htpasswd | coding, admin | Infra only |
| **Porkbun / DNS** | `PORKBUN_*` | coding (human-supervised) | Rotate if pasted; Tier 2 |
| **MinIO** | `MINIO_*` | data, coding | Archives / attachments |
| **Grafana** | `GRAFANA_*` | admin, coding | Embed URLs ok; admin password Tier 2 |

---

## Cell isolation rules

1. A skill tagged to cell `wnn-client` may **not** read `GHL_MCO_*` credentials.
2. `personal-admin` content never promotes to business agent memory without Boss re-scope.
3. Cross-cell summaries (CEO brief) are Tier 0 aggregates — no raw PII dumps into Telegram.
4. Archive `scope=personal` → Admin/Hermes only; no GHL/RE agents.

---

## Authority checklist (before running a skill)

```text
[ ] Assignee ∈ skill.agents
[ ] Active cell ∈ skill.cells (or Boss override logged)
[ ] Required credentials present in vault/.env for THAT cell
[ ] Action risk ≤ skill.tier_autonomous OR approval row exists
[ ] Heartbeats enabled only if RESUME-POLICY satisfied
[ ] No secret material written into chat / SOUL / MEMORY
```

---

## Quick matrix (skill → primary agent → max auto tier)

See [CATALOG.md](./CATALOG.md) for the full table. Summary:

| Domain | Primary agent | Auto ≤ |
|--------|---------------|--------|
| CEO brief / inbox review / reminders | Admin | 1 |
| Approvals decide | Admin (Boss UI / Gerald) | 0 propose / 3 decide=human |
| GHL CRM actions | GHL cell agent | 1 draft / 2 send |
| Deploy / Traefik / Hermes install | Coding | 1 plan / 2 apply |
| ChatGPT archive classify/link | Admin / Data | 1 |
| Outbound email/SMS | Comms or GHL | 2 |
| Credential rotate / wipe | — | 3 human |
