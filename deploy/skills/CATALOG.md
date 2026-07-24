# Clawsum skills — catalog & access matrix

Canonical list. Authority rules: [AUTHORITY.md](./AUTHORITY.md).

**Legend:** Auto = max tier skill may complete without Gerald approval.

| Skill | Primary agent(s) | Cells | Auto | Credentials (prefixes) | Notes |
|-------|------------------|-------|------|------------------------|-------|
| `ceo-daily-brief` | admin, hermes | clawsum-platform | 0 | PAPERCLIP, POSTGRES, TELEGRAM | Morning board |
| `hermes-proactive-drive` | hermes, admin | platform, personal-admin | 1 | PAPERCLIP, POSTGRES | Ask questions; no Tier2 exec |
| `overwatch-approvals` | admin, paperclip | * | 0 | POSTGRES | Decide = human |
| `paperclip-task-routing` | admin, paperclip, hermes, planning | * | 1 | PAPERCLIP | Route by cell |
| `resume-policy-gate` | admin, paperclip, coding | platform | 0 | PAPERCLIP | Heartbeats gated |
| `gmail-inbox-review` | admin, hermes, data | platform, personal-admin | 1 | GMAIL, POSTGRES | Per-email analysis |
| `gmail-sync-triage` | admin, data | platform | 1 | GMAIL, POSTGRES, PAPERCLIP, OPENAI? | Cron path |
| `people-places-crm` | admin, data | * | 1 | POSTGRES | CRM layer |
| `reminders-boss-nudge` | admin | platform, personal-admin | 1 | POSTGRES, TELEGRAM | Daily nudges |
| `chatgpt-archive` | admin, data, hermes | platform, personal-admin | 1 | POSTGRES, PAPERCLIP | No memory dump |
| `cell-isolation-check` | admin, coding, planning | * | 0 | POSTGRES | Pre-flight |
| `ghl-lead-ops` | ghl, admin | wnn-client | 1 | GHL_* cell-only | Send=T2 |
| `ghl-reengage` | ghl, admin | wnn-client | 1 | GHL_* | REENGAGE.md |
| `vocalitic-health` | coding, admin | vocalitic, hardware-local-ai | 0 | OPENCLAW, POSTGRES | Restart=T2 |
| `roofing-storm-intel` | realestate, research | roofing-os | 1 | POSTGRES, GHL? | Outreach=T2 |
| `real-estate-pipeline` | realestate, research | real-estate | 1 | POSTGRES, ARCADEDB | Offers=T2/3 |
| `commerce-fastbuy` | comms, planning | acceptai-fastbuy | 1 | POSTGRES | Ads/refunds=T2 |
| `techtasia-planning` | planning, admin | techtasia | 1 | PAPERCLIP, POSTGRES | |
| `personal-admin` | admin, hermes | personal-admin | 1 | GMAIL, calendar | Private |
| `hardware-local-ai` | coding, admin | hardware-local-ai | 0 | docker/host | |
| `vps-deploy-clawsum` | coding, admin | platform | 1 | SSH, POSTGRES, OPENCLAW | Prod apply=T2 |
| `hermes-cockpit-install` | coding, admin | platform | 1 | container exec | |
| `domain-traefik-ops` | coding, admin | platform | 1 | PORKBUN, BOSS_OPS | DNS=T2 |
| `grafana-health` | admin, coding | platform (+infra cells) | 0 | GRAFANA | |
| `postgres-ops-schema` | coding, data, admin | platform | 1 | POSTGRES | Wipe=T3 |
| `telegram-ops-notify` | admin | platform | 1 | TELEGRAM | No secrets |
| `draft-comms-approval-gated` | comms, ghl, admin, hermes | * | 1 | cell-specific | Send=T2 |
| `clawsum-com-funnel` | coding, comms, admin | platform | 1 | SSH | Pricing=T2 |
| `credential-hygiene` | admin, coding | platform | 0 | — | Rotate=T2/3 |
| `audit-log-review` | admin, paperclip | * | 0 | POSTGRES | |
| `openclaw-agent-config` | coding, admin | platform | 1 | OPENCLAW, GOG, GMAIL | |
| `minio-archive-store` | data, coding, admin | platform | 1 | MINIO, POSTGRES | |
| `research-brief` | research, planning, admin, hermes | * | 0 | LLM optional | |

## Agent → skills (who should load what)

| Agent | Skills to prioritize |
|-------|----------------------|
| **Admin** | ceo-daily-brief, gmail-*, reminders, overwatch-approvals, personal-admin, telegram-ops-notify, credential-hygiene, cell-isolation-check |
| **Hermes** | hermes-proactive-drive, chatgpt-archive (query), gmail-inbox-review (summarize), paperclip-task-routing, draft-comms-approval-gated, research-brief |
| **Paperclip** | paperclip-task-routing, overwatch-approvals, resume-policy-gate, audit-log-review |
| **Coding** | vps-deploy-*, hermes-cockpit-install, domain-traefik-ops, openclaw-agent-config, postgres-ops-schema, vocalitic-health, hardware-local-ai, clawsum-com-funnel |
| **Data** | gmail-sync-triage, chatgpt-archive, people-places-crm, postgres-ops-schema, minio-archive-store |
| **GHL** | ghl-lead-ops, ghl-reengage, draft-comms-approval-gated |
| **RE** | roofing-storm-intel, real-estate-pipeline |
| **Comms** | draft-comms-approval-gated, commerce-fastbuy, clawsum-com-funnel (copy) |
| **Research** | research-brief, roofing-storm-intel, real-estate-pipeline |
| **Planning** | techtasia-planning, paperclip-task-routing, cell-isolation-check |

## Envisioned next (stubs — add when ready)

| Future skill | Agent | Creds | Why deferred |
|--------------|-------|-------|--------------|
| `discord-hq` | admin, comms | DISCORD_* | Channel layout deferred |
| `voice-jarvis` | hermes, admin | SPEECH_*, ELEVENLABS_* | Voice deferred |
| `ghl-mco-rei` / `ghl-ave-rei` | ghl-* | per-slug PIT | Instance overlays |
| `calendar-sync` | admin | Google Calendar OAuth | Not wired |
| `stripe-billing` | admin | STRIPE_* | Founding payments |
| `obsidian-promote` | admin, research | obsidian path | Partial today |

## Advice (authority)

1. **Default deny send/deploy.** Any skill that can change the outside world stops at draft + approval.
2. **One cell per credential set.** GHL PITs never shared; Admin may *see* summaries across cells but not raw PITs in chat.
3. **Hermes ≠ superuser.** Hermes proposes Paperclip work; Coding/GHL execute with scoped creds.
4. **Cursor coding agent** may use `vps-deploy-*` / funnel skills with SSH — still treat production apply as Boss-visible.
5. **Tier 3** (wipe, banking, legal) has **no** skill that auto-completes — human only.
6. Mirror into `.cursor/skills/` only if you want IDE auto-discovery; keep editing here.
