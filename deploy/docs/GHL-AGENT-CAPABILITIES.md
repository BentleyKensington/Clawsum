# GHL agent — authorized task catalog

**Default agent:** `ghl` (one GHL location per template instance)  
**MCP endpoint:** `https://services.leadconnectorhq.com/mcp/`  
**Config:** `deploy/config/ghl-accounts.json` + `.env` (`GHL_PIT`, `GHL_LOCATION_ID`)

The GHL agent is **CRM-generic** — not trained on a vertical. It hooks to any GoHighLevel sub-account, runs read-first audits, builds re-engage lists, and documents findings in Obsidian. Optional REI heuristics: `ghl-strategic-audit.py --vertical rei` (instance overlay only).

---

## Authorization tiers

| Tier | Operator approval | Agent may |
|------|-------------------|-----------|
| **A — Read / audit** | Pre-approved for audit tasks | All `get`, `search`, `fetch`, `list`, `check` tools |
| **B — Operational write** | Per task or batch | `create`, `update`, `upsert`, `add-tags`, `send message` |
| **C — Marketing / content** | Explicit per campaign | Blog, email template, social post tools |
| **D — Platform (non-MCP)** | Per runbook | Obsidian reports, Postgres findings, Paperclip tasks |

---

## Core CRM tasks (any vertical)

| Area | Tasks | MCP / scripts |
|------|-------|----------------|
| **Contacts** | List, get, create, update, upsert, tag | `contacts_*` |
| **Opportunities** | Pipelines, search, update stages | `opportunities_*` |
| **Conversations** | Search threads, read messages, send reply (Tier B) | `conversations_*` |
| **Location** | Verify location, list custom fields | `locations_*` |
| **Calendar** | Events, appointment notes | `calendars_*` |
| **Strategic audit** | Re-engage list, landline detection, recommendations | `ghl-strategic-audit.py --slug ghl` |
| **Read-only audit** | MCP inventory → Obsidian + Postgres | `ghl-audit-readonly.py --slug ghl` |
| **Telegram re-engage** | Read `REENGAGE.md` in workspace (no search/browser) | Agent `read` tool |

---

## Strategic audit (generic default)

```bash
python3 /docker/clawsum/scripts/ghl-strategic-audit.py --slug ghl
python3 /docker/clawsum/scripts/ghl-strategic-audit.py --slug ghl --use-llm
python3 /docker/clawsum/scripts/ghl-strategic-audit.py --slug ghl --apply-landline-tags
```

Outputs:

- `obsidian/GHL/{folder}/Audits/YYYY-MM-DD-strategic-analysis.md`
- `obsidian/GHL/{folder}/Recommendations/YYYY-MM-DD-reengage-leads.md`
- Workspace `REENGAGE.md` for Telegram summaries

---

## Provisioning

```bash
# .env: GHL_PIT, GHL_LOCATION_ID, GHL_DB_PASSWORD
bash /docker/clawsum/scripts/provision-ghl-accounts.sh
python3 /docker/clawsum/scripts/verify-ghl-isolation.py
docker compose restart openclaw-gateway
```

---

## Telegram binding

```bash
python3 /docker/clawsum/scripts/bind-ghl-telegram.py --slug ghl --from-sessions
# or explicit group id from .env: GHL_TELEGRAM_GROUP_ID
```

In group: @mention the bot. For re-engage: agent reads `REENGAGE.md` only.

---

## Multi-account (instance overlay)

For multiple locations, copy `deploy/config/ghl-accounts.instance.rei.example.json` → `config/ghl-accounts.json` on the VPS and re-run provision. Not the generic template default.

See `deploy/examples/instance-overlays/` for vertical playbooks (e.g. REI).
