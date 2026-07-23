# Paperclip Overwatch — Phase 3

Paperclip is the **control plane**: tasks, routing, approvals, budgets, audit, business-cell registry.  
Hermes/JARVIS is the **face**; OpenClaw is the **hands**. This doc starts Phase 3 of the CEO Overwatch build.

---

## Goals (Phase 3)

| Goal | Acceptance |
|------|------------|
| Business cell registry in Postgres | Seeded profiles; isolatable by `slug` |
| Approval objects with risk tiers 0–3 | Create / approve / reject via API or script |
| Audit log for governed actions | Every approval decision + OpenClaw result summary |
| Hermes creates tasks via Paperclip | Chat → Paperclip issue linked to `business_id` |
| Boss UI + Discord later show approvals | Browser first; Discord channel later |

---

## Risk tiers (enforce in policy + code)

| Tier | Meaning | Agent may |
|------|---------|-----------|
| **0** | Read-only / internal | Auto |
| **1** | Reversible / draft | Auto or light notify |
| **2** | Client-facing, money, prod, data write | **Gerald approval required** |
| **3** | Banking, legal, delete DB, credential wipe | **Human only — never autonomous** |

---

## Schema (ops overwatch)

Applied by `postgres-init/12-overwatch.sql` (new installs) or:

```bash
psql "$DATABASE_URL" -f /docker/clawsum/deploy/postgres-init/12-overwatch.sql
# or on VPS after copy:
psql -U clawsum -d clawsum -f /docker/clawsum/postgres-init/12-overwatch.sql
```

Tables:

- `ops.businesses` — cell registry  
- `ops.overwatch_agents` — agent ↔ business mapping (Paperclip agent id optional)  
- `ops.approvals` — risk-tiered approval cards  
- `ops.audit_logs` — immutable-ish event trail  

Archive tables (ChatGPT import) land in a later migration (`13-chatgpt-archive.sql`).

---

## Seed business cells

```bash
python3 /docker/clawsum/scripts/seed-business-cells.py
python3 /docker/clawsum/scripts/seed-business-cells.py --list
```

Default seeds (instance overlay — no secrets):

| slug | name |
|------|------|
| `personal-admin` | Personal Admin |
| `hardware-local-ai` | Hardware / Local AI |
| `wnn-client` | WNN / Client |
| `roofing-os` | Roofing OS |
| `vocalitic` | Vocalitic |
| `techtasia` | Techtasia |
| `acceptai-fastbuy` | AcceptAI / FastBuy |
| `real-estate` | Real Estate |

Credentials stay in `.env` / vault per cell — never in these rows.

---

## Scripts (Phase 3 starter)

| Script | Role |
|--------|------|
| `seed-business-cells.py` | Upsert business profiles |
| `overwatch-create-approval.py` | Create Tier 1–2 approval + audit row |
| `overwatch-decide-approval.py` | approve / reject / revise |
| `paperclip-resume-work.py` | Unpause agents ([RESUME-POLICY.md](./RESUME-POLICY.md)) |

Wire path (next increments):

1. Hermes / cockpit → `POST` create Paperclip issue + optional `ops.approvals` row  
2. Boss UI comment / cockpit button → decide approval  
3. Only then OpenClaw adapter runs tool  

Mock adapters are fine until heartbeats resume.

---

## Paperclip policy (short)

```text
All business-affecting tasks must have a business cell (ops.businesses.slug).
Tier 2 requires Gerald approval before OpenClaw execution.
Tier 3 is never assigned to agents.
Log: requester, cell, agent, tool, data touched, approval, result.
```

Full CEO routing prompt: instance overlay / Hermes SOUL — see CEO Overwatch execution report §16–18.

---

## Resume + overwatch

Do **not** enable heartbeats until [RESUME-POLICY.md](./RESUME-POLICY.md) checklist is done.  
Overwatch schema can be applied while paused — it does not start agents.

---

## Related

- [CEO-COCKPIT.md](./CEO-COCKPIT.md)  
- [PAPERCLIP-SETUP.md](./PAPERCLIP-SETUP.md)  
- [HERMES-POLICY.md](./HERMES-POLICY.md)  
- [GHL-MULTI-ACCOUNT-PLAN.md](./GHL-MULTI-ACCOUNT-PLAN.md) — cell isolation pattern (Approach A)
