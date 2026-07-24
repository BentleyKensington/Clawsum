# Overwatch CRM — cells, people, places, tasks, emails, reminders

Governed ops layer for CEO Overwatch. **Paperclip** remains task execution truth; Postgres `ops.*` is the local mirror Hermes uses to drive questions.

## Entities

| Entity | Table | Role |
|--------|--------|------|
| **Cells** | `ops.businesses` | Business / platform isolation (seed via `seed-business-cells.py`) |
| **People** | `ops.people` | Contacts, Boss, orgs, system mailboxes |
| **Places** | `ops.places` + `ops.person_places` | Offices, regions, properties |
| **Tasks** | `ops.tasks` | Local pending work + clarification questions (links Paperclip) |
| **Emails** | `ops.emails` | `clawsums@gmail.com` archive + triage + review |
| **Reminders** | `ops.reminders` | Daily Boss nudges (Telegram) |

Schema: `postgres-init/14-ops-crm.sql` (extends `05-ops-email.sql`, `06-ops-reminders.sql`, `12-overwatch.sql`).

## Cells (seeded)

| slug | Notes |
|------|--------|
| `clawsum-platform` | Empire control plane + admin inbox |
| `personal-admin` | Gerald personal (not client CRM) |
| `hardware-local-ai` | GPU / local models |
| `wnn-client` | WNN / GHL |
| `roofing-os` | CEOroof |
| `vocalitic` | Voice AI |
| `techtasia` | Techtasia |
| `acceptai-fastbuy` | Commerce |
| `real-estate` | Owned RE (non-WNN) |

## Apply + seed (VPS)

```bash
cd /docker/clawsum
# ensure email/reminders schemas exist first if fresh:
#   psql … -f postgres-init/05-ops-email.sql
#   psql … -f postgres-init/06-ops-reminders.sql
#   psql … -f postgres-init/12-overwatch.sql

bash scripts/run-overwatch-crm.sh
# or with full inbox pass:
bash scripts/run-overwatch-crm.sh --review-inbox --sync-first
```

Requires `GMAIL_*` in `.env` for sync/review — see [GMAIL-ADMIN-SETUP.md](./GMAIL-ADMIN-SETUP.md).  
Mailbox: **`clawsums@gmail.com`** (`GMAIL_ADMIN_ADDRESS`).

## Review all inbox mail

```bash
# Sync then classify every inbox message → cell + person + local task + questions
python3 scripts/gmail-sync.py --backfill          # optional historical
python3 scripts/gmail-inbox-review.py --inbox-only --sync-first --markdown --create-reminders

# Re-run everything
python3 scripts/gmail-inbox-review.py --all --markdown
```

What review does **for every email**:

1. Builds a structured **analysis** (intent, summary, recommendation, priority, signals, Boss questions)
2. Stores it on `ops.emails` (`analysis_*` columns + `analysis_report` markdown)
3. Upserts `ops.email_reviews` (one durable report row per message)
4. Assigns **business cell** + upserts **people** from From:
5. Sets `review_status` (`reviewed` | `needs_boss` | `ignored`)
6. Creates **`ops.tasks`** (+ optional reminders) when action is required

```bash
# Markdown report with a section for EACH email:
python3 scripts/gmail-inbox-review.py --inbox-only --all --markdown

# Also write one .md file per message:
python3 scripts/gmail-inbox-review.py --inbox-only --all --report-dir /docker/clawsum/data/inbox-reports
```


## Hermes standing orders

See `examples/hermes-cockpit/SOUL.md`:

1. Paperclip board first  
2. Inbox (`clawsums@gmail.com`) action items + reminders  
3. Link people/places/cells  
4. Ask one sharp question per stuck item  

Cockpit: `GET /api/plugins/clawsum-cockpit/inbox` and `/crm`.

## Related

- [GMAIL-ADMIN-SETUP.md](./GMAIL-ADMIN-SETUP.md)
- [PAPERCLIP-OVERWATCH.md](./PAPERCLIP-OVERWATCH.md)
- [CHATGPT-ARCHIVE.md](./CHATGPT-ARCHIVE.md)
- [HERMES-POLICY.md](./HERMES-POLICY.md)
