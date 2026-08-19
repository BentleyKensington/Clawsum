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
| `ghl-weekly-rei-report` | ghl, admin | wnn-client | 1 | GHL_*, POSTGRES | Nightly audit + 07:30 send MCO+AVE |
| `vocalitic-health` | coding, admin | vocalitic, hardware-local-ai | 0 | OPENCLAW, POSTGRES | Restart=T2 |
| `roofing-storm-intel` | realestate, research | roofing-os | 1 | POSTGRES, GHL? | Outreach=T2 |
| `real-estate-pipeline` | realestate, research | real-estate | 1 | POSTGRES, ARCADEDB | Offers=T2/3 |
| `commerce-fastbuy` | comms, planning | acceptai-fastbuy | 1 | POSTGRES | Ads/refunds=T2 |
| `techtasia-planning` | planning, admin | techtasia | 1 | PAPERCLIP, POSTGRES | |
| `personal-admin` | admin, hermes | personal-admin | 1 | GMAIL, calendar | Private |
| `hardware-local-ai` | coding, admin, media | hardware-local-ai | 0 | docker/host | VRAM queue w/ media |
| `vps-deploy-clawsum` | coding, admin | platform | 1 | SSH, POSTGRES, OPENCLAW | Prod apply=T2 |
| `hermes-cockpit-install` | coding, admin | platform | 1 | container exec | |
| `domain-traefik-ops` | coding, admin | platform | 1 | PORKBUN, BOSS_OPS | DNS=T2 |
| `grafana-health` | admin, coding | platform (+infra cells) | 0 | GRAFANA | |
| `postgres-ops-schema` | coding, data, admin | platform | 1 | POSTGRES | Wipe=T3 |
| `telegram-ops-notify` | admin | platform | 1 | TELEGRAM | Dual-write; no secrets |
| `discord-hq` | admin, comms, coding | platform | 1 | DISCORD | Preferred mobile; provision=T1, bindings=T2 |
| `draft-comms-approval-gated` | comms, ghl, admin, hermes | * | 1 | cell-specific | Send=T2 |
| `clawsum-com-funnel` | coding, comms, admin | platform | 1 | SSH | Pricing=T2 |
| `credential-hygiene` | admin, coding | platform | 0 | — | Rotate=T2/3 |
| `audit-log-review` | admin, paperclip | * | 0 | POSTGRES | |
| `openclaw-agent-config` | coding, admin | platform | 1 | OPENCLAW, GOG, GMAIL | |
| `minio-archive-store` | data, coding, admin, media | platform, media-production | 1 | MINIO, POSTGRES | Media blobs OK |
| `research-brief` | research, planning, admin, hermes | * | 0 | LLM optional | |
| `inbound-adopt-evaluate` | research, planning, hermes, admin, coding | platform, techtasia | 1 | OPENAI, POSTGRES, PAPERCLIP | Overlap = compare; mockups = product input |
| `skill-forge` | coding, planning, admin, hermes | platform, techtasia | 1 | PAPERCLIP | Turn adopt/steal into SKILL.md + assignee |
| `media-trends-brief` | media, research, hermes | media-production | 0 | LLM optional | Trends → Paperclip only |
| `media-ingest-watch` | media, coding | media-production, hardware-local-ai | 1 | MINIO, POSTGRES, YTDLP, FFMPEG | Phase 0 |
| `media-transcribe` | media | media-production, hardware-local-ai | 1 | WHISPER, MINIO, POSTGRES | Phase 0 |
| `media-package-seo` | media, research, hermes | media-production | 1 | POSTGRES, LLM, PAPERCLIP | Phase 1 AEO/GEO/SEO |
| `media-shorts-factory` | media | media-production, hardware-local-ai | 1 | FFMPEG, WHISPER, MINIO | Phase 2; Cut/Storm optional |
| `media-longform-resolve` | media | media-production, hardware-local-ai | 1 | RESOLVE, FFMPEG, MINIO | Phase 3 |
| `media-generative-broll` | media | media-production, hardware-local-ai | 1 | COMFY, MINIO | Phase 4; paid cloud=T2 |
| `media-publish` | media, admin | media-production | 1 draft / **2 publish** | YOUTUBE, PAPERCLIP, POSTGRES | Gerald gate |
| `pentest-threat-model` | pentest, admin, coding | clawsum-platform | 0 | PAPERCLIP, POSTGRES | Living threat register |
| `pentest-surface-scan` | pentest, coding | clawsum-platform | 1 | PAPERCLIP, POSTGRES, GRAFANA | Read-only; no exploits |
| `pentest-report` | pentest, admin | clawsum-platform | 1 | PAPERCLIP, POSTGRES, MINIO | Findings → reports/ |
| `pentest-notify` | pentest, admin | clawsum-platform | 1 | DISCORD, TELEGRAM | High/Critical + security events |
| `data-scraper` | data | clawsum-platform | 1 | BRIGHTDATA, POSTGRES | Tool on Data — not its own agent |
| `data-osint` | data, pentest | clawsum-platform | 0 | POSTGRES | OSINT + global monitor |
| `data-chat-extract` | data, hermes | clawsum-platform | 1 | POSTGRES | Chat → memory facts |
| `graphify-obsidian` | data, research, hermes | clawsum-platform | 1 | POSTGRES, ARCADEDB | 3D vault / Graphify |
| `agent-daily-review` | hermes, admin, planning | * | 1 | PAPERCLIP, POSTGRES | Feeds morning brief |
| `hermes-daily-alert` | hermes, admin | clawsum-platform | 1 | DISCORD, TELEGRAM, POSTGRES | Leverage / money alerts |
| `legal-review` | legal, admin | clawsum-platform | 0 | — | File/sign = T3 |
| `content-repurpose` | content, media | media-production | 1 | MINIO, PAPERCLIP | Publish via Social |
| `ppc-ads-ops` | ads, comms | acceptai-fastbuy, wnn-client | 1 | — | Spend = T2 |
| `bookkeeper-ledger` | bookkeeper, admin | clawsum-platform | 0 | — | Pay/wire = T3 |
| `seo-aeo-geo` | seo, research | clawsum-platform | 1 | — | GSC / GMB / panel |
| `funnel-builder` | funnel, comms, coding | clawsum-platform | 1 | SSH | Prod publish = T2 |
| `calendar-ops` | calendar, admin | personal-admin, platform | 1 | — | Invite send = T2 |
| `social-posting` | social, content, comms | media-production | 1 draft / **2 post** | YOUTUBE, META, TIKTOK, PAPERCLIP, POSTGRES | Schedule or now |
| `content-idea-intake` | hermes, content, research, admin | media-production, platform | 1 | POSTGRES, PAPERCLIP | Boss idea → factory |
| `content-evergreen-research` | research, content, hermes, media | media-production | 1 | POSTGRES, PAPERCLIP | Trend format + evergreen angle |
| `content-pack` | content, research, media, hermes | media-production | 1 | POSTGRES, PAPERCLIP | Topic, flyer, story, script |
| `content-produce` | media, content | media-production, hardware-local-ai | 1 | FFMPEG, MINIO, POSTGRES | Video + first frame + thumb |
| `content-daily-factory` | content, media, research, social, hermes | media-production | 1 | POSTGRES, FFMPEG | Daily evergreen cron |
| `llm-compare` | llm-lab, coding, research | clawsum-platform | 1 | OPENAI, OPENROUTER | Bake-off scorecard |
| `llm-free-vs-paid` | llm-lab, hermes, coding, research | clawsum-platform | 1 | OPENROUTER, OPENAI | Default cheap |
| `llm-research-watch` | llm-lab, research, coding | clawsum-platform | 1 | OPENROUTER, NVIDIA, DEEPGRAM | Weekly + on demand |
| `deepgram-voice-eval` | llm-lab, vocalitic, vapi | vocalitic, platform | 1 | DEEPGRAM, ELEVENLABS | Paid eval notify |
| `spec-interview` | hermes, admin, planning | * | 1 | PAPERCLIP, POSTGRES | Until spec card complete |
| `vocalitic-product-ops` | vocalitic, coding | vocalitic | 1 | VOCALITIC_SSH_*, PATH | Deploy=T2 |
| `acceptai-product-ops` | acceptai, coding | acceptai-fastbuy | 1 | ACCEPTAI_* | Deploy=T2 |
| `product-ssh-ops` | vocalitic, acceptai, coding, rocco | product cells | 0 | *_SSH_* | Read-only default |
| `closebot-api-operator` | closebot, ghl | wnn-client | 1 | CLOSEBOT_API_KEY | Send=T2 |
| `vapi-account-ops` | vapi, vocalitic | vocalitic, platform | 1 | VAPI_API_KEY | Outbound=T2 |
| `sellthebizfast-buybox` | sellthebizfast, research | sellthebizfast | 1 | — | Score listings |
| `sellthebizfast-cim-dd` | sellthebizfast, legal, comms | sellthebizfast | 1 | — | Send/LOI gated |
| `rocco-ops-sentry` | rocco, pentest, admin | platform | 1 | GRAFANA, OPENCLAW | No exploits |
| `rocco-ring-official` | rocco, admin | platform | 0 | RING_* | Official API only |
| `printful-ops` | printful, shopify | acceptai-fastbuy | 1 | PRINTFUL_API_TOKEN | Catalog mutate=T2 |
| `shopify-ops` | shopify, printful | acceptai-fastbuy | 1 | SHOPIFY_* | Theme/pay=T2 |
| `google-photos-picker` | printful, media, shopify, admin | media, commerce | 1 | GOG, GMAIL | No full-library |
| `browser-research-deep` | research, llm-lab, sellthebizfast | * | 0 | LLM optional | Escalate if thin |
| `cockpit-hud` | coding, hermes, admin | clawsum-platform | 1 | — | Gauges + marquee |

## Agent → skills (who should load what)

| Agent | Skills to prioritize |
|-------|----------------------|
| **Admin** | ceo-daily-brief, gmail-*, reminders, overwatch-approvals, personal-admin, discord-hq, telegram-ops-notify, credential-hygiene, cell-isolation-check |
| **Clawsum** | hermes-proactive-drive, chatgpt-archive (query), gmail-inbox-review (summarize), paperclip-task-routing, draft-comms-approval-gated, research-brief, inbound-adopt-evaluate, skill-forge (propose), media-package-seo (propose), media-trends-brief |
| **Paperclip** | paperclip-task-routing, overwatch-approvals, resume-policy-gate, audit-log-review |
| **Coding** | vps-deploy-*, hermes-cockpit-install, domain-traefik-ops, openclaw-agent-config, skill-forge, postgres-ops-schema, vocalitic-health, hardware-local-ai, clawsum-com-funnel |
| **Data** | gmail-sync-triage, chatgpt-archive, people-places-crm, postgres-ops-schema, minio-archive-store, data-scraper, data-osint, data-chat-extract, graphify-obsidian |
| **GHL** | ghl-lead-ops, ghl-reengage, ghl-weekly-rei-report, draft-comms-approval-gated |
| **RE** | roofing-storm-intel, real-estate-pipeline |
| **Comms** | draft-comms-approval-gated, commerce-fastbuy, clawsum-com-funnel (copy) |
| **Research** | research-brief, inbound-adopt-evaluate, roofing-storm-intel, real-estate-pipeline, media-trends-brief, content-evergreen-research |
| **Planning** | techtasia-planning, paperclip-task-routing, inbound-adopt-evaluate, skill-forge, cell-isolation-check |
| **Media** | media-ingest-watch, media-transcribe, media-package-seo, media-shorts-factory, media-longform-resolve, media-generative-broll, media-publish, media-trends-brief, content-produce, minio-archive-store, hardware-local-ai |
| **Pentest** | pentest-threat-model, pentest-surface-scan, pentest-report, pentest-notify, credential-hygiene, audit-log-review, cell-isolation-check |
| **Legal** | legal-review |
| **Content** | content-idea-intake, content-evergreen-research, content-pack, content-produce, content-daily-factory, content-repurpose |
| **Ads** | ppc-ads-ops, commerce-fastbuy |
| **Bookkeeper** | bookkeeper-ledger |
| **SEO** | seo-aeo-geo, media-package-seo |
| **Funnel** | funnel-builder, clawsum-com-funnel |
| **Calendar** | calendar-ops, personal-admin |
| **Social** | social-posting, content-daily-factory, discord-hq, draft-comms-approval-gated |
| **LLM Lab** | llm-compare, llm-free-vs-paid, llm-research-watch, deepgram-voice-eval, browser-research-deep |
| **Vocalitic** | vocalitic-product-ops, vocalitic-health, product-ssh-ops, deepgram-voice-eval |
| **AcceptAI** | acceptai-product-ops, commerce-fastbuy, product-ssh-ops |
| **CloseBot** | closebot-api-operator |
| **VAPI** | vapi-account-ops |
| **Printful** | printful-ops, google-photos-picker |
| **Shopify** | shopify-ops, google-photos-picker, printful-ops |
| **SellTheBizFast** | sellthebizfast-buybox, sellthebizfast-cim-dd, spec-interview, browser-research-deep, legal-review |
| **Rocco Secure** | rocco-ops-sentry, rocco-ring-official, pentest-notify, grafana-health |

## Control plane (Hermes ↔ OpenClaw)

```text
Boss / Hermes UI  →  Paperclip issue (assignee=media, cell=media-production)
                  →  OpenClaw agent `media` executes skills
                  →  drafts/renders auto (Tier 0–1)
                  →  publish / paid spend → ops.approvals + Gerald (Tier 2)
```

Hermes does **not** run FFmpeg itself. It routes. OpenClaw `media` manages the studio tools.

## Envisioned next (stubs — add when ready)

| Future skill | Agent | Creds | Why deferred |
|--------------|-------|-------|--------------|
| `voice-jarvis` | hermes, admin | SPEECH_*, ELEVENLABS_* | Voice deferred (TTS live in cockpit) |
| `ghl-mco-rei` / `ghl-ave-rei` | ghl-* | per-slug PIT | Instance overlays |
| `calendar-sync` | calendar | Google Calendar OAuth | Shell `calendar-ops` exists; OAuth next |
| `stripe-billing` | admin | STRIPE_* | Founding payments |
| `obsidian-promote` | admin, research | obsidian path | Partial today |
| `media-google-photos-picker` | media, printful, admin | Google Photos Picker | **Skill `google-photos-picker` now exists** |

## Advice (authority)

1. **Default deny send/deploy/publish.** Any skill that can change the outside world stops at draft + approval.
2. **One cell per credential set.** GHL PITs never shared; Admin may *see* summaries across cells but not raw PITs in chat.
3. **Hermes ≠ superuser.** Hermes proposes Paperclip work; Coding/GHL/**Media** execute with scoped creds.
4. **Cursor coding agent** may use `vps-deploy-*` / funnel skills with SSH — still treat production apply as Boss-visible.
5. **Tier 3** (wipe, banking, legal) has **no** skill that auto-completes — human only.
6. Mirror into `.cursor/skills/` only if you want IDE auto-discovery; keep editing here.
