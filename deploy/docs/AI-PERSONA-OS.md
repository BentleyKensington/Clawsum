# AI Persona OS — Clawsum template

**Status:** Included in the generic deploy template  
**Runtime path (VPS):** `/docker/clawsum/data/.openclaw/workspace-{agent}/`  
**Seed script:** `deploy/scripts/seed-persona-os.sh`  
**GHL overlay:** `deploy/scripts/provision-ghl-accounts.py` + `deploy/templates/ghl/`

The **AI Persona OS** is the per-agent workspace layer OpenClaw loads at session start: identity, boundaries, workflows, memory layout, and Obsidian promotion rules. It is **not** optional for a working Clawsum stack.

---

## Core agents (seeded by `seed-persona-os.sh`)

| Agent id | Identity | Key files |
|----------|----------|-----------|
| `admin` | Clawsum Admin | SOUL, ESCALATION, USER, AGENTS (from admin workspace) |
| `coding` | Clawsum Coding | SOUL, ESCALATION, WORKFLOWS, BOOT, IDENTITY |
| `data` | Clawsum Data | SOUL, ESCALATION, WORKFLOWS, BOOT, IDENTITY |
| `realestate` | Clawsum Real Estate | SOUL, ESCALATION, WORKFLOWS, BOOT, IDENTITY |
| `ghl` | GHL Ops | SOUL, ESCALATION, WORKFLOWS, BOOT, IDENTITY (+ provision overlay) |
| `comms` | Clawsum Comms | SOUL, ESCALATION, WORKFLOWS, BOOT, IDENTITY |
| `research` | Clawsum Research | SOUL, ESCALATION, WORKFLOWS, BOOT, IDENTITY |
| `planning` | Clawsum Planning | SOUL, ESCALATION, WORKFLOWS, BOOT, IDENTITY |
| `paperclip` | Clawsum Paperclip | SOUL, ESCALATION, WORKFLOWS, BOOT, IDENTITY |

Each workspace also gets:

- `memory/` — daily `YYYY-MM-DD.md` notes  
- `notes/` — scratch → promote to Obsidian  
- `projects/` — in-flight work  
- `DATABASE.md` — from `seed-workspace-db-docs.sh`  
- Shared copies of `SECURITY.md`, `USER.md`, `AGENTS.md` (from admin, except admin itself)

---

## GHL agent persona (template + provision)

Generic template ships **one** `ghl` agent in `deploy/config/ghl-accounts.json`.

After `provision-ghl-accounts.py`, the GHL workspace is overwritten from `deploy/templates/ghl/`:

| File | Purpose |
|------|---------|
| `SOUL.md` | Account scope, CRM missions, read-first policy |
| `AGENTS.md` | Telegram file paths (`REENGAGE.md`), tool constraints |
| `TOOLS.md` | Allowed/denied tools, audit command |
| `WORKFLOWS.md` | Re-engage + audit runbook |
| `ESCALATION.md` | Boss approval, cross-agent handoffs |
| `DATABASE.md` | Isolated `ghl.{schema}` role |
| `OBSIDIAN.md` | Vault folder rules |
| `BOOT.md` | Session startup checklist |
| `REENGAGE.md` | Written by `ghl-strategic-audit.py` (runtime, not in git) |

Optional **instance overlay** (e.g. REI multi-account): copy `deploy/config/ghl-accounts.instance.rei.example.json` → `config/ghl-accounts.json` and add vertical playbook from `deploy/examples/instance-overlays/`.

---

## Bootstrap order

1. `bootstrap-new-vps.sh` — core stack  
2. `seed-persona-os.sh` — all core personas  
3. `setup-obsidian-vault.sh` / `setup-obsidian-vault.py` — vault folders  
4. `seed-workspace-db-docs.sh` — DATABASE.md per agent  
5. `configure-openclaw.py` — agent list + tool policies  
6. `provision-ghl-accounts.sh` — when `GHL_*_PIT` present in `.env`

---

## Repo artifacts vs runtime

| In git (template) | Instance only (never commit) |
|-------------------|------------------------------|
| `deploy/scripts/seed-persona-os.sh` | `data/.openclaw/workspace-*/memory/*.md` |
| `deploy/templates/ghl/*.md` | `data/.openclaw/openclaw.json` (generated) |
| `deploy/templates/persona/MANIFEST.md` | Codex OAuth / `auth-profiles.json` |
| | `.env`, PIT tokens, Telegram bindings |

See [CREDENTIALS-EXCLUSION.md](./CREDENTIALS-EXCLUSION.md).

---

## Optional sandbox

`ghl-template` sandbox is **not** in the generic default. Instance configs may add a `"sandbox"` block to `ghl-accounts.json` for read-only template reference.
