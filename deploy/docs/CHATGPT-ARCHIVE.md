# ChatGPT archive — proactive intent layer

Governed import of Gerald’s ChatGPT history. Used to **flag personal vs business**, **link Paperclip tasks**, and **drive clarifying questions** via Hermes.  
**Never** dump the export wholesale into Hermes memory.

## Pipeline

```text
ChatGPT export ZIP / conversations.json
  → import-chatgpt-export.py          # ops.conversations + messages
  → classify-chatgpt-archive.py       # scope, cell, work_status, questions
  → link-archive-to-paperclip.py      # match open/done issues → status
  → archive-proactive-brief.py        # Hermes / cockpit brief
```

## Schema

Apply once on Postgres:

```bash
psql -U clawsum -d clawsum -f /docker/clawsum/postgres-init/13-chatgpt-archive.sql
# or flat VPS layout:
psql -U clawsum -d clawsum -f /docker/clawsum/postgres-init/13-chatgpt-archive.sql
```

Tables (schema `ops`): `chatgpt_imports`, `conversations`, `messages`, `conversation_chunks`, `extracted_facts`, `extracted_tasks`, `archive_task_links`.

Key conversation fields:

| Field | Meaning |
|-------|---------|
| `scope` | `personal` \| `business` \| `mixed` \| `unknown` |
| `work_status` | `pending` \| `in_progress` \| `completed` \| `blocked` \| `abandoned` \| `other` |
| `primary_business_id` | Cell from `ops.businesses` |
| `clarification_questions` | What Hermes should ask Boss |
| `paperclip_issue_*` | Linked issue when matched |
| `approved_for_hermes` | Explicit promote-to-memory gate (default false) |

## Import (VPS)

```bash
# Copy export to VPS (do not commit the ZIP)
mkdir -p /docker/clawsum/data/chatgpt-archive
# scp chatgpt-*.zip root@HOST:/docker/clawsum/data/chatgpt-archive/

cd /docker/clawsum
# Supports classic conversations.json OR sharded conversations-NNN.json inside the ZIP
python3 scripts/import-chatgpt-export.py /docker/clawsum/data/chatgpt-archive/YOUR-export.zip
# Or a directory of extracted shards:
# python3 scripts/import-chatgpt-export.py /docker/clawsum/data/chatgpt-archive/shards
python3 scripts/classify-chatgpt-archive.py
python3 scripts/link-archive-to-paperclip.py
python3 scripts/archive-proactive-brief.py --markdown

# Promote durable business/mixed facts → ops.memory_facts (+ Arcade). Skips personal.
python3 scripts/promote-archive-to-memory.py --dry-run --limit 20
python3 scripts/promote-archive-to-memory.py --resume
```

Requires `POSTGRES_*` and `PAPERCLIP_COMPANY_ID` in `/docker/clawsum/.env`.

**Note:** Large OpenAI exports may ship as `conversations-000.json` … `conversations-NNN.json` (not a single `conversations.json`). The importer merges all shards and skips `shared_conversations.json`.

**Memory promote:** `promote-archive-to-memory.py` is Boss-approved extraction into the Phase 1 memory graph. It never processes `scope=personal`, scrubs secrets, and sets `approved_for_hermes_memory` on written facts.

## Promote to memory graph

```bash
# Dry-run candidate count (skips personal)
python3 /docker/clawsum/scripts/promote-archive-to-memory.py --dry-run

# Full Boss-approved pass (resumable)
python3 /docker/clawsum/scripts/promote-archive-to-memory.py --resume

# Priority only (pending/blocked/in_progress)
python3 /docker/clawsum/scripts/promote-archive-to-memory.py --priority-only --resume
```

Writes:
- `ops.memory_facts` / `ops.memory_episodes` (`source_kind=chatgpt`)
- `ops.extracted_facts` with `approved_for_hermes_memory=true` for durable business facts
- Arcade `Fact` / `Episode` / `MemoryEntity` mirrors
- Sets `conversations.approved_for_hermes=true` when ≥1 fact extracted

Logs: `/docker/clawsum/data/chatgpt-archive/promote-full-*.log`

---

## Hermes proactive behavior

Install SOUL into the Hermes home (Paperclip container):

```bash
install -m 644 /docker/clawsum/examples/hermes-cockpit/SOUL.md /paperclip/.hermes/SOUL.md
# or: bash scripts/install-hermes-cockpit.sh   # copies SOUL when present
```

Hermes must:

1. Look at the **Paperclip task list** first.
2. Cross-link related archive items (same intent / cell / keywords).
3. Infer intent; ask **sharp questions** to move pending → clear next action.
4. Keep **personal** items out of business agents and durable memory.

Cockpit API: `GET /api/plugins/clawsum-cockpit/archive` returns the same brief JSON.

## Poll archive → Obsidian memory

Inbox/task analysis already **consults** `ops.conversations` + promoted facts on every item (skips personal).

To refresh the vault Gerald reads:

```bash
# Incremental pulse → Admin/Archive + Admin/Memory/from-chatgpt-archive.md
python3 /docker/clawsum/scripts/poll-archive-to-obsidian.py

# Also extract new durable facts into ops.memory_facts first
python3 /docker/clawsum/scripts/poll-archive-to-obsidian.py --promote

# Hourly cron
bash /docker/clawsum/scripts/install-archive-obsidian-cron.sh
```

New ChatGPT export → `import-chatgpt-export.py` → next poll writes the delta into Obsidian. Nightly dream then compresses facts into `Admin/Memory/*-dream.md`.

## Safety

- Sensitive regex flags messages at import; still treat personal as private.
- Rotate any API keys that appeared inside ChatGPT chats after import review.
- Porkbun / other secrets pasted in chat are **compromised** — rotate outside this pipeline.
- Resume OpenClaw agents only per [RESUME-POLICY.md](./RESUME-POLICY.md).

## Related

- [HERMES-POLICY.md](./HERMES-POLICY.md)
- [PAPERCLIP-OVERWATCH.md](./PAPERCLIP-OVERWATCH.md)
- [CEO-OVERWATCH.md](./CEO-OVERWATCH.md)
