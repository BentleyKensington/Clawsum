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
| **Clawsum** | `hermes` | platform (opt-in long runs) | Proactive drive, archive questions — **Boss authorized only** |
| **Clawsum Paperclip** | `paperclip` | platform | Task routing, board hygiene |
| **Clawsum Coding** | `coding` | `hardware-local-ai`, `vocalitic`, platform deploy | VPS, cockpit, OpenClaw config |
| **Clawsum Data** | `data` | platform + analytics cells | Postgres reports, ETL, ArcadeDB |
| **Clawsum GHL** (+ instance overlays) | `ghl` / `ghl-*` | `wnn-client` (+ MCO/AVE/WNN) | CRM, re-engage, pipelines |
| **Clawsum RE** | `realestate` | `real-estate`, `roofing-os` | Deals, storm/roofing intel |
| **Clawsum Comms** | `comms` | `acceptai-fastbuy`, drafts | Outbound drafts (send = Tier 2) |
| **Clawsum Research** | `research` | any (read) | Competitive / brief research |
| **Clawsum Planning** | `planning` | `techtasia`, platform roadmap | Priorities, cell planning |
| **Clawsum Media** | `media` | `media-production`, `hardware-local-ai` | Ingest, Whisper, FFmpeg Shorts, Resolve/Velorn polish, publish packs |
| **Clawsum Content** | `content` | `media-production` | Evergreen packs — topic, flyer, story, script |
| **Clawsum Social** | `social` | `media-production` | Schedule / post (Tier 2) |
| **Clawsum Pentest** | `pentest` | `clawsum-platform` | Defensive scans |
| **Rocco Secure** | `rocco` | `clawsum-platform` | Sentry, official Ring, freeze/token watch |
| **Clawsum LLM Lab** | `llm-lab` | platform | Free vs paid; weekly vendor watch |
| **Vocalitic** | `vocalitic` | `vocalitic` | Product — v1m12 + SSH |
| **AcceptAI** | `acceptai` | `acceptai-fastbuy` | Product runtime |
| **CloseBot** | `closebot` | `wnn-client` | Agency API; send = T2 |
| **VAPI** | `vapi` | vocalitic / platform | Assistants/calls; outbound = T2 |
| **Printful** | `printful` | commerce | Catalog + Photos Picker |
| **Shopify** | `shopify` | commerce | Admin API |
| **SellTheBizFast** | `sellthebizfast` | `sellthebizfast` | Acquisitions |

**Clawsum UI** (CEO chat face / Hermes) proposes; Paperclip assigns; **OpenClaw agents execute**.  
Media work: Hermes (or Admin) opens Paperclip → assignee **Clawsum Media** (`media`) → OpenClaw runs skills on local GPU / MinIO — publish stays Tier 2.  
Content factory: Hermes intake → **Research** (angle) → **Content** (pack) → **Media** (video / first frame / thumb) → **Social** schedule or post (Tier 2). Daily evergreen cron seeds production if Boss sent nothing.  
Security: **Rocco** sentries and notifies; **Pentest** runs defensive scans. No exploits. Ring = official Appstore API only. See [ROCCO-SECURE.md](../docs/ROCCO-SECURE.md) and [CLAWSUM-SECURITY-QA.md](../docs/CLAWSUM-SECURITY-QA.md).

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
| **Telegram** | `TELEGRAM_*` | admin (reports), cell bots | Dual-write until Discord verified; no secrets in group chat |
| **Discord** | `DISCORD_*`, `NOTIFY_CHANNELS` | admin (reports), openclaw gateway | Preferred mobile HQ; no secrets in channels |
| **OpenClaw gateway** | `OPENCLAW_*` | coding, admin | Config changes Tier 2 |
| **LLM API** | `OPENAI_*`, `OPENROUTER_*` | triage cron, research | Prefer Codex OAuth for agents |
| **Traefik / ops auth** | `BOSS_OPS_*`, htpasswd | coding, admin | Infra only |
| **Porkbun / DNS** | `PORKBUN_*` | coding (human-supervised) | Rotate if pasted; Tier 2 |
| **MinIO** | `MINIO_*` | data, coding, media | Archives / attachments / media blobs |
| **Grafana** | `GRAFANA_*` | admin, coding | Embed URLs ok; admin password Tier 2 |
| **YouTube publish** | `YOUTUBE_*` OAuth | media, social (publish skills only) | Upload/schedule = Tier 2 |
| **Social publish** | `META_*`, `TIKTOK_*` | social | Post/schedule = Tier 2 |
| **Media tooling** | `FFMPEG_BIN`, `WHISPER_*`, `COMFY_*`, `RESOLVE_*`, `YTDLP_*` | media, coding (install) | Local paths / endpoints; no secrets in chat |
| **Voice / music spend** | `ELEVENLABS_*`, `DEEPGRAM_*`, cloud GPU keys | media, vocalitic, llm-lab | Paid generate = Tier 2 |
| **CloseBot** | `CLOSEBOT_API_KEY` | closebot | Header `X-CB-KEY`; send = T2 |
| **VAPI** | `VAPI_API_KEY` | vapi | Bearer; outbound = T2 |
| **Printful / Shopify** | `PRINTFUL_*`, `SHOPIFY_*` | printful, shopify | Catalog/theme = T2 |
| **Product SSH** | `VOCALITIC_SSH_*`, `ACCEPTAI_SSH_*` | vocalitic, acceptai, coding | Read-only default |
| **Ring official** | `RING_CLIENT_*`, `RING_REFRESH_TOKEN` | rocco | Appstore Private Apps only |

---

## Cell isolation rules

1. A skill tagged to cell `wnn-client` may **not** read `GHL_MCO_*` credentials.
2. `personal-admin` content never promotes to business agent memory without Boss re-scope.
3. Cross-cell summaries (CEO brief) are Tier 0 aggregates — no raw PII dumps into Telegram/Discord.
4. Archive `scope=personal` → Admin/Hermes only; no GHL/RE agents.
5. `media-production` owns studio blobs/credentials; do not mix client GHL media into personal-admin without Boss re-scope.

---

## Authority checklist (before running a skill)

```text
[ ] Assignee ∈ skill.agents
[ ] Active cell ∈ skill.cells (or Boss override logged)
[ ] Required credentials present in vault/.env for THAT cell
[ ] Action risk ≤ skill.tier_autonomous OR approval row exists
[ ] Jarvis batch gate: full steps logged; Approve All once OR preapproved_fast / skip_batch

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
| Media ingest / transcribe / package / render drafts | Media | 0–1 |
| Content factory pack / daily produce | Content, Media | 1 |
| Publish YouTube / Shorts / social | Media, Social | 2 (+ Gerald) |
| Pentest scan / report / notify (defensive) | Pentest | 0–1 |
| Outbound email/SMS | Comms or GHL | 2 |
| Credential rotate / wipe | — | 3 human |
