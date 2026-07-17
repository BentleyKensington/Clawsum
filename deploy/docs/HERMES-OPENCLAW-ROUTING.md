# Hermes + OpenClaw — complementary routing (not either/or)

Clawsum uses **both** on purpose. The debate online (“replace OpenClaw with Hermes” or vice versa) misses that they solve **different layers**.

Related: [HERMES-POLICY.md](./HERMES-POLICY.md) · [MASTER-TASK-LIST.md](./MASTER-TASK-LIST.md) · [DATA-ARCADEDB-VS-POSTGRES.md](./DATA-ARCADEDB-VS-POSTGRES.md)

---

## Highest-and-best use together

```text
                    BOSS
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
   Boss UI (Paperclip)      Telegram / Control UI
   tasks · approvals        realtime · channels
         │                         │
         │    ┌────────────────────┘
         ▼    ▼
    ┌─────────────────────────────────────┐
    │           OpenClaw gateway           │
    │  9 specialists · tools · Telegram    │
    │  Gmail · Postgres · Obsidian per agent │
    └─────────────────┬───────────────────┘
                      │ session paperclip:hermes (long jobs only)
                      ▼
    ┌─────────────────────────────────────┐
    │     Hermes Agent (optional UI :9119)  │
    │  deep autonomy · skills · cron · chat │
    │  explore dashboard — not default path │
    └─────────────────────────────────────┘
```

| Layer | Tool | Best for |
|-------|------|----------|
| **Governance** | **Paperclip / Boss UI** | What work exists, who owns it, Boss approvals, budgets |
| **Daily ops** | **OpenClaw agents** | Telegram, domain tools, CRM, Gmail, scoped Postgres |
| **Long autonomous sweeps** | **Hermes via OpenClaw** (`paperclip:hermes`) | 50+ step refactors, multi-file research when Boss authorizes |
| **Hermes dashboard** | **Exploration / emergency** | Config, sessions, embedded TUI — **parallel**, not replacement |
| **Batch automation** | **Cron + LangGraph** | Gmail triage, reports, ETL — no chat session |
| **Graph / similarity** | **ArcadeDB** | Comps, RAG chunks, “find like this” — not CRM rows |

**Do not** route routine Boss tasks to Hermes. **Do not** drop OpenClaw because Hermes has a UI. **Do** use Hermes UI to see what Nous shipped and keep direct access “just in case.”

---

## How we structured vs ideal

| Area | Current Clawsum | Ideal (same architecture, gaps to close) |
|------|-----------------|------------------------------------------|
| Boss surface | Paperclip ✅ | + ops portal auth |
| OpenClaw specialists | 9 agents + ghl ✅ | Telegram smoke sign-off |
| Hermes execution | `openclaw_gateway` headless ✅ | + dashboard for Boss preview |
| Hermes `hermes_local` | Not used ✅ | Stay off unless you want API-only isolation |
| LLM labels | Documented ⬜ | `paperclip-analyze-assign-boss.py` writes `llm:*` |
| ArcadeDB | Container + ingest script ✅ | Wire **data** agent ETL after Postgres rows exist |
| LangGraph | Tier 2 live ✅ | Wire graphs to real triage + research |

---

## ArcadeDB ETL — best use with the stack

**Postgres = system of record.** **ArcadeDB = graph + vectors + similarity.**

### When to ingest

| After… | ArcadeDB gets… |
|--------|----------------|
| RE listing in Postgres `realestate.listings` | `Listing` vertex + embedding property |
| Sold comp scraped | `Comp` vertex + `EDGE` to nearby `Listing` |
| Research brief chunked | `SourceChunk` + citation edges |
| GHL contact campaign graph (optional) | `Contact` ↔ `Campaign` edges |

### ETL flow (recommended)

```text
data agent / cron
  → normalize row in Postgres (canonical $, dates, status)
  → build embedding (batch: llm:cheap or local)
  → arcadedb-ingest.py --json '{ "_type":"Comp", "_id":"...", ... }'
  → realestate agent queries: "comps within 1mi" via graph, not cross-DB SQL
```

**Not yet wired:** cron from Postgres → JSONL → `arcadedb-ingest.py`. Container runs; ingest script works; **no production ETL schedule**.

**Different from “replace Postgres”:** ArcadeDB does not hold Gmail triage or GHL pipeline status — those stay SQL.

---

## Hermes dashboard (added now)

| Step | Command |
|------|---------|
| Install | `bash scripts/install-hermes-dashboard.sh` |
| Start | `bash scripts/hermes-dashboard.sh start` |
| Public URL | `https://hermes.${DOMAIN}` via `setup-ops-portal-traefik.sh` |
| SSH fallback | `ssh -L 9119:127.0.0.1:9119 clawsum` → http://localhost:9119 |

Dashboard auth: Traefik basic auth (outer) + Hermes own login if configured (inner).

**Production Hermes jobs** still go through Boss UI assignee — dashboard does not replace Paperclip.

---

## Decision cheat sheet

| Boss wants… | Route to… |
|-------------|-----------|
| Quick Telegram answer | OpenClaw specialist |
| Tracked task with approval | Paperclip → OpenClaw agent |
| 50+ step autonomous job | Paperclip → Clawsum Hermes (authorized) |
| See Hermes features / manual session | Hermes dashboard |
| Nightly email classify | Cron `gmail-triage.py` (not Codex) |
| Find similar properties | Postgres row → ArcadeDB graph query |
