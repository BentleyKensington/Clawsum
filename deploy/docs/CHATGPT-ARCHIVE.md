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
python3 scripts/import-chatgpt-export.py /docker/clawsum/data/chatgpt-archive/YOUR-export.zip
python3 scripts/classify-chatgpt-archive.py
python3 scripts/link-archive-to-paperclip.py
python3 scripts/archive-proactive-brief.py --markdown
```

Requires `POSTGRES_*` and `PAPERCLIP_COMPANY_ID` in `/docker/clawsum/.env`.

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

## Safety

- Sensitive regex flags messages at import; still treat personal as private.
- Rotate any API keys that appeared inside ChatGPT chats after import review.
- Porkbun / other secrets pasted in chat are **compromised** — rotate outside this pipeline.
- Resume OpenClaw agents only per [RESUME-POLICY.md](./RESUME-POLICY.md).

## Related

- [HERMES-POLICY.md](./HERMES-POLICY.md)
- [PAPERCLIP-OVERWATCH.md](./PAPERCLIP-OVERWATCH.md)
- [CEO-OVERWATCH.md](./CEO-OVERWATCH.md)
