# ArcadeDB vs PostgreSQL — what goes where

Clawsum uses **both**. They are not interchangeable: Postgres is the system of record for structured business data; ArcadeDB is for **relationships, graph traversal, and vector search**.

---

## Quick rule

| Use **PostgreSQL** when… | Use **ArcadeDB** when… |
|--------------------------|-------------------------|
| Rows have fixed columns (CRM, deals, emails, tasks) | You need “who is connected to what” across many hops |
| SQL reports, cron, ETL, backups | Similarity search (comps, embeddings, “find like this”) |
| ACID transactions, joins with dates/money | Knowledge graph (property ↔ comp ↔ contact ↔ campaign) |
| Agent must **never** cross-query another agent’s DB | Research briefs linked as nodes, not flat tables |

**Default:** if unsure, start in **Postgres**. Promote to ArcadeDB when you need graph or vector queries.

---

## By domain

### Admin / ops (`clawsum` DB, schema `ops`)

| Data | Store | Why |
|------|-------|-----|
| Gmail archive | **Postgres** `ops.emails` | Structured, triage status, cron |
| Boss reminders / snooze | **Postgres** `ops.reminders` | Daily cron, SQL filters |
| Paperclip issue IDs (links) | Postgres reference only | Source of truth is Paperclip |
| Audit log (optional) | **Postgres** | Time-series friendly |

### Coding (`clawsum.coding`)

| Data | Store | Why |
|------|-------|-----|
| Deploy logs, CI metadata | **Postgres** | Tabular |
| Repo dependency graph | **ArcadeDB** (optional) | If you model packages/services as graph |

### Data (`clawsum.data`)

| Data | Store | Why |
|------|-------|-----|
| Scraper runs, job status, webhooks | **Postgres** | ETL pipelines |
| Raw scrape staging tables | **Postgres** | CSV/JSON → SQL |
| Embeddings for “similar listings” | **ArcadeDB** | Vector index |
| Bright Data job config | **Postgres** | Config rows |

### Real estate (`realestate` DB — isolated)

| Data | Store | Why |
|------|-------|-----|
| Deals, listings, contacts (tables) | **Postgres** `deals`, `listings`, `contacts` | Agent-owned SQL |
| Property ↔ comp ↔ market area links | **ArcadeDB** | Graph: “comps within 1mi of deal X” |
| Comp similarity / vector search | **ArcadeDB** | k-NN on embeddings |
| Underwriting numbers | **Postgres** | Fixed schema |

### GHL (`ghl` DB — isolated)

| Data | Store | Why |
|------|-------|-----|
| Contacts, pipelines, opportunities | **Postgres** | CRM tabular (API sync) |
| Contact ↔ campaign ↔ tag relationships | **ArcadeDB** (optional) | Complex automations graph |
| Message templates, send log | **Postgres** | Compliance + reporting |

### Research (`clawsum.research`)

| Data | Store | Why |
|------|-------|-----|
| Brief metadata, URLs, dates | **Postgres** | |
| Source documents + chunks + embeddings | **ArcadeDB** | RAG / “related sources” |
| Citation graph (source A cites B) | **ArcadeDB** | Graph |

### Comms / Planning

| Data | Store | Why |
|------|-------|-----|
| Drafts, campaigns, calendars | **Postgres** | |
| Topic / narrative links | **ArcadeDB** (later) | Optional |

---

## Cross-domain rule (locked)

- **realestate** and **ghl** agents do **not** query each other’s Postgres DBs.
- Crossover via **Paperclip tasks**, **data ETL exports**, or **ArcadeDB** only when Boss approves a shared graph namespace.
- **Admin** does not own domain tables — routes and links only.

---

## Sync pattern (when both are used)

```text
Postgres (source row: listing_id=123)
    → data agent builds embedding
    → ArcadeDB vertex Listing:123 + edges to Comps, Contacts
Postgres remains canonical for $, dates, status
ArcadeDB for "find 10 similar sold comps in graph"
```

---

## Schema-on-arrival (no upfront schema required)

ArcadeDB is **not** fully schemaless: you need at least a **document type** before inserts behave well. Clawsum uses a thin **ingest layer** so agents/ETL can send JSON without hand-writing SQL DDL first.

### How it works

```text
Postgres row OR agent JSON
    → arcadedb-ingest.py
        1. CREATE DATABASE clawsum_graph IF NOT EXISTS
        2. CREATE DOCUMENT TYPE "<_type>" IF NOT EXISTS
        3. CREATE PROPERTY "<type>"."<field>" <INFERRED> IF NOT EXISTS
        4. INSERT INTO "<type>" CONTENT { ... }
    → ArcadeDB Studio (inspect)
```

| JSON field | Meaning |
|------------|---------|
| `_type` | **Required** — document type name (`Listing`, `Comp`, `SourceChunk`, …) |
| `_id` | Optional stable id → stored as `clawsum_id` |
| Other keys | Properties; nested objects/lists stored as JSON strings |

### Run on VPS

```bash
# Example single record
export ARCADEDB_ROOT_PASSWORD='…'   # from /docker/clawsum/.env
python3 /docker/clawsum/scripts/arcadedb-ingest.py \
  --json '{"_type":"Listing","_id":"re-123","address":"1 Main St","price":450000}'

# Batch JSONL from data agent ETL
python3 /docker/clawsum/scripts/arcadedb-ingest.py --file /tmp/listings.jsonl
```

**Boss browse:** `ssh -L 2480:127.0.0.1:2480 clawsum` → http://localhost:2480 (root + `ARCADEDB_ROOT_PASSWORD`).

### Rules (still locked)

- **Postgres remains canonical** for money, dates, CRM status, Gmail triage.
- ArcadeDB is for **graph/vector/similarity** — ingest copies or derived fields, not the only copy of deal terms.
- Promote messy JSON to typed Postgres tables when reports need SQL; keep ArcadeDB for “find similar” and edges.

### Later: graph edges

When you add relationships (`Comp` → `Listing`), extend ingest or a second script to `CREATE EDGE TYPE …` and `CREATE EDGE` after both vertex types exist. Vectors: add embedding properties + index once property types are stable.

---

## Phase status

| Component | Status |
|-----------|--------|
| Postgres multi-DB + schemas | ✅ Live |
| `ops.emails`, `ops.reminders` | ✅ Schema ready |
| ArcadeDB container | ✅ Running on `:2480` |
| Schema-on-arrival ingest | ✅ Script `arcadedb-ingest.py` |
| RE comps ETL → ArcadeDB | ⬜ Wire `data` agent / cron |
| Research RAG chunks | ⬜ Phase 4+ |

Next: populate Postgres RE tables, then JSONL export → `arcadedb-ingest.py` for comps graph.
