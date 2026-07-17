# Persona OS file manifest (template repo)

Files that define or seed the AI Persona OS. Runtime copies live under `data/.openclaw/workspace-{agent}/` on the VPS.

## Seed script

- `deploy/scripts/seed-persona-os.sh` — core agents (admin, coding, data, realestate, **ghl**, comms, research, planning, paperclip)
- `deploy/scripts/seed-workspace-db-docs.sh` — `DATABASE.md` per agent
- `deploy/scripts/provision-ghl-accounts.py` — GHL template render from `deploy/templates/ghl/`

## Per-agent files (runtime)

| File | Purpose |
|------|---------|
| `SOUL.md` | Role, scope, boundaries |
| `IDENTITY.md` | Name, emoji, vibe |
| `ESCALATION.md` | Boss approval triggers |
| `WORKFLOWS.md` | Domain runbooks |
| `BOOT.md` | Session startup |
| `AGENTS.md` | Tool/file access rules (GHL: from template) |
| `TOOLS.md` | GHL only — MCP + path cheatsheet |
| `DATABASE.md` | DB isolation rules |
| `OBSIDIAN.md` | GHL only — vault promotion |
| `SECURITY.md` | Copied from admin |
| `USER.md` | Copied from admin |
| `memory/YYYY-MM-DD.md` | Daily notes (runtime) |
| `REENGAGE.md` | GHL audit output (runtime) |

## GHL template sources (`deploy/templates/ghl/`)

- SOUL.md, AGENTS.md, TOOLS.md, WORKFLOWS.md, ESCALATION.md, DATABASE.md, OBSIDIAN.md

## Documentation

- `deploy/docs/AI-PERSONA-OS.md` — full Persona OS guide
- `deploy/docs/CREDENTIALS-EXCLUSION.md` — secrets policy
