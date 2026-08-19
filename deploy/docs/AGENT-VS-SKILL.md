# When to create an agent vs a skill

**Default: skill first.** A new OpenClaw/Paperclip agent is expensive (workspace, credentials, cell, morning brief, Team tile). Only split when the work is a *business* with its own risk, brand, or runtime.

## Use a **skill** on an existing agent when

- It is a **tool** (scraper, MinIO, Gmail sync, Graphify export, model bake-off helper)
- Same credentials and cell as the parent agent
- Same approval tier as the parent’s other work
- One person would say “Data, go scrape that” — not “ask the Scraper company”

**Scraper we built → Data agent skill** (`data-scraper`). Same as `minio-archive-store`. Not a Vocalitic-style product.

## Use a **dedicated agent** when

- Distinct **profession + liability** (legal, bookkeeper, pentest)
- Distinct **outbound identity** (social posting, PPC spend, SEO/GMB as a brand)
- Its own **product/runtime** (Vocalitic, Media GPU studio)
- Would confuse the parent agent’s SOUL if mixed in (calendar across cells vs Admin inbox)

## Current calls

| Thing | Verdict | Why |
|-------|---------|-----|
| Scraper / crawler | **Skill → Data** | Tool. No brand, no spend. |
| OSINT / chat extract / GSC pull | **Skill → Data** (OSINT may assist Pentest) | Collection, not a firm. |
| Graphify / 3D vault | **Skill → Data + Research** | Visualizer over Obsidian/Arcade. |
| Legal review | **Agent `legal`** | Privilege, contracts, Tier 3 adjacent. |
| Bookkeeper | **Agent `bookkeeper`** | Money, books, Tier 2–3. |
| PPC / Ads | **Agent `ads`** | Paid spend = Tier 2, own platforms. |
| SEO / AEO / GEO | **Agent `seo`** | GSC, GMB, knowledge panel — own craft. |
| Funnel builder | **Agent `funnel`** | Offers/pages/CRO as a product motion. |
| Content repurpose | **Agent `content`** | Pipeline distinct from Media render + Comms send. |
| Calendar | **Agent `calendar`** | Cross-cell scheduling, not just Admin mail. |
| Social | **Agent `social`** | Post/reply = public voice, Tier 2. |
| LLM compare / bake-off | **Agent `llm-lab`** | Continuous eval, not a one-off Coding script. |
| Vocalitic | **Keep/promote agent** | Product + runtime (v1m12). |
| Media studio | **Keep agent** | GPU/runtime + publish gate. |
| AcceptAI | **Keep/promote agent** | Product + runtime, not just FastBuy copy. |
| CloseBot / VAPI / Printful / Shopify | **Keep agents** | Own APIs and brands. |
| SellTheBizFast | **Agent** | Liability + outbound identity. |
| Rocco Secure | **Agent** | Sentry + Ring; pentest stays scans. |
| LLM Lab | **Keep agent** | Continuous eval, not a one-off Coding script. |
| Deep research browser | **Skill** | Research + LLM Lab. |
| Google Photos Picker | **Skill** | Media / Printful / Shopify. |

Revisit if a skill grows its own credentials, cron fleet, and Boss-facing KPI — then promote to an agent.
