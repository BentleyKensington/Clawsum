# GHL multi-account agents — plan & template

**Status:** Phase 1 — **MCO REI operational**; AVE/WNN provisioned, awaiting Boss PIT + locationId  
**Bookmarked for later:** Boss Paperclip backlog clarifications, Obsidian SSHFS on PC  
**Accounts (initial):** MCO REI, AVE REI, WNN REI (+ one copy-paste template)

---

## Should we do this now or finish Wave 1/2 first?

**Proceed now — but only Phase 0 + Phase 1 (read-only audit).** Do not block on full Wave 1/2 or Boss backlog.

| Track | Do now? | Why |
|-------|---------|-----|
| **GHL template + 3 agents** | **Yes** | High business value; Phase 7 was always planned; MCP is official and PIT-scoped |
| **Wave 1** (Obsidian PC, backlog replies) | **Later** (bookmarked) | Does not block GHL wiring |
| **Wave 2** (MinIO, LangGraph, ArcadeDB) | **Parallel / later** | Helpful but not required for first GHL audit |
| **OpenClaw 2026.6.10 upgrade** | **Done** (2026-07-01) | Ran after MCO GHL smoke test; see `upgrade-platform-versions.sh` |

**Gate before any write/automation changes in GHL:** Boss reviews read-only audit recommendations per account.

---

## One container per account vs one gateway?

You asked for a **unique agent container per GHL account**. On Clawsum today there is **one** `openclaw-gateway` container and **one** generic `ghl` agent.

| Approach | Isolation | Ops cost | Recommendation |
|----------|-----------|----------|----------------|
| **A. One gateway, multiple GHL agents** (`ghl-mco-rei`, …) | Strong — separate workspace, PIT, MCP config, Postgres schema, Telegram group, Paperclip agent | **Low** | **Default** |
| **B. One gateway container per GHL account** | Strongest process isolation | **High** (3× memory, 3× ports, 3× pairing/Telegram) | Only if compliance requires |
| **C. Single `ghl` agent, switch account in prompt** | Weak — credential bleed risk | Lowest | **Not recommended** |

**Recommendation:** Treat each account as a **first-class agent** (Approach A). Same Docker gateway is fine; isolation is at **credentials + workspace + DB + memory**, not necessarily separate containers.

If you later require Approach B, the **template stays the same** — only compose adds `openclaw-gateway-ghl-mco` services.

---

## Per-account template (copy-paste)

Slug examples: `mco-rei`, `ave-rei`, `wnn-rei`.

### 1. OpenClaw agent

| Item | Pattern |
|------|---------|
| Agent id | `ghl-{slug}` e.g. `ghl-mco-rei` |
| Workspace | `/home/node/.openclaw/workspace-ghl-{slug}` |
| Persona | `SOUL.md` — REI-centric GHL operator (see below) |
| MCP | Official GHL MCP — one PIT + locationId per agent |
| Tools | `read`, `write`, `browser`; **no** `exec` until Boss approves |
| Telegram | Dedicated group per account (recommended) |

### 2. MCP config (OpenClaw)

Official endpoint: `https://services.leadconnectorhq.com/mcp/`

```json
{
  "mcpServers": {
    "ghl-{slug}": {
      "url": "https://services.leadconnectorhq.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${GHL_{SLUG}_PIT}",
        "locationId": "${GHL_{SLUG}_LOCATION_ID}"
      }
    }
  }
}
```

**PIT scopes (read-only audit minimum):** locations, contacts, opportunities, conversations, calendars, custom fields — **view** scopes first; add write scopes only after Boss approves remediation.

Store secrets in `/docker/clawsum/.env`:

```env
GHL_MCO_REI_PIT=pit-...
GHL_MCO_REI_LOCATION_ID=...
GHL_AVE_REI_PIT=pit-...
GHL_AVE_REI_LOCATION_ID=...
GHL_WNN_REI_PIT=pit-...
GHL_WNN_REI_LOCATION_ID=...
```

### 3. Postgres

One database `ghl`, **separate schema per account** (matches RE isolation pattern):

- `ghl.mco_rei_*` — sync snapshots, audit runs, recommendations
- `ghl.ave_rei_*`
- `ghl.wnn_rei_*`

Legacy generic `ghl` agent data can stay in `public` or migrate once.

### 4. Obsidian

```text
obsidian/GHL/
  _template/           ← copy for new accounts
  MCO-REI/
  AVE-REI/
  WNN-REI/
```

Deliverables: `Audits/YYYY-MM-DD-automation-review.md`, `Recommendations/lost-opportunities.md`.

### 5. Paperclip

| Paperclip agent | OpenClaw id |
|-----------------|-------------|
| Clawsum GHL — MCO REI | `ghl-mco-rei` |
| Clawsum GHL — AVE REI | `ghl-ave-rei` |
| Clawsum GHL — WNN REI | `ghl-wnn-rei` |

Keep generic **Clawsum GHL** paused/deprecated — use account agents only.

## Provision (VPS)

```bash
bash /docker/clawsum/scripts/provision-ghl-accounts.sh
python3 /docker/clawsum/scripts/verify-ghl-isolation.py
cd /docker/clawsum && docker compose restart openclaw-gateway
```

See `env.ghl.example` for credential env vars.

## Relationship to existing `ghl` agent

Today: generic `ghl` is **sandboxed** as `ghl-template` (read-only, no Telegram/MCP). Live work uses three account agents.

Plan:

1. ✅ Add three account agents from template (`provision-ghl-accounts.py`)
2. ✅ Deprecate generic `ghl` → `ghl-template` sandbox
3. Do **not** resume heartbeats until one account audit completes successfully

### 6. REI persona (all three accounts)

Each agent `SOUL.md` includes:

- **REI context:** motivated sellers, disposition, follow-up SLAs, pipeline stages (lead → appt → offer → contract → close)
- **Focus:** automations, workflows, missed calls/texts, stale opportunities, tag hygiene
- **Never:** cross-query `realestate` DB or another GHL account’s schema
- **Handoff:** property/deal underwriting → Paperclip task to **Clawsum RE** (not direct)

---

## First job per account (read-only audit)

When PIT + locationId are provided:

1. **Inventory** — pipelines, workflows/automations, calendars, custom fields
2. **Contact health** — no activity 30/60/90d, open opportunities without recent touch, unworked inbound
3. **Automation gaps** — broken triggers, missing follow-ups, duplicate workflows
4. **Recommendations** — prioritized list (quick wins vs structural); **no writes** until Boss approves
5. **Output** — Obsidian audit doc + optional Paperclip issue per recommendation batch

---

## What we need from Boss (to go beyond Phase 0)

For **each** of MCO REI, AVE REI, WNN REI:

| Field | Example |
|-------|---------|
| **Private Integration Token (PIT)** | `pit-…` |
| **Location ID** | sub-account ID |
| **Display name** | MCO REI |
| **Telegram group** (optional) | create or reuse group id |

Confirm: **read-only audit first** vs allow workflow edits in v1.

---

## Implementation scripts (to build when credentials arrive)

| Script | Purpose |
|--------|---------|
| `provision-ghl-accounts.py` / `.sh` | Workspace, persona, MCP, schema, Obsidian, Paperclip agents |
| `verify-ghl-isolation.py` | Automated isolation checks |
| `ghl-strategic-audit.py --slug mco-rei` | Strategic REI analysis + re-engage list (newest leads first) |
| `ghl-audit-readonly.py --slug mco-rei` | Read-only MCP audit → Obsidian + Postgres |
| `templates/ghl-account/` | SOUL, SECURITY, ESCALATION, WORKFLOWS, MCP snippet |

---

## Related docs

- [PLATFORM-MASTER-REPORT.md](./PLATFORM-MASTER-REPORT.md) §15 — GHL MCP Phase 7
- [SETUP-REMAINING.md](./SETUP-REMAINING.md) — Wave 1/2 checklist (bookmarked items)
- [GHL MCP (official)](https://help.gohighlevel.com/support/solutions/articles/155000005741-how-to-use-the-highlevel-mcp-server)
- [HERMES-POLICY.md](./HERMES-POLICY.md) — Hermes stays on gateway; not used for GHL audits by default
