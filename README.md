# Clawsum

Self-hosted multi-agent operations platform: **OpenClaw** specialist agents, **Paperclip** task orchestration, Postgres, Obsidian, and optional domain packs (GHL CRM, Gmail, etc.).

This repository is a **generic deploy template**. Instance secrets, OAuth tokens, and business data never belong in git.

## Quick start

```bash
git clone https://github.com/BentleyKensington/Clawsum.git
cd Clawsum
cp deploy/env.example /docker/clawsum/.env   # fill all values on the VPS
bash deploy/scripts/bootstrap-new-vps.sh
bash deploy/scripts/verify-platform.sh
```

On the VPS, the stack typically lives at `/docker/clawsum` with `deploy/` artifacts copied or synced flat (`scripts/`, `config/`, `templates/`).

## Key docs

| Doc | Purpose |
|-----|---------|
| [deploy/docs/PLATFORM-DEPLOY-TEMPLATE.md](deploy/docs/PLATFORM-DEPLOY-TEMPLATE.md) | Multi-VPS template spec and completion tiers |
| [deploy/docs/AI-PERSONA-OS.md](deploy/docs/AI-PERSONA-OS.md) | Per-agent workspace / persona layer |
| [deploy/docs/CREDENTIALS-EXCLUSION.md](deploy/docs/CREDENTIALS-EXCLUSION.md) | What must stay out of git |
| [deploy/docs/GHL-AGENT-CAPABILITIES.md](deploy/docs/GHL-AGENT-CAPABILITIES.md) | Generic GHL CRM agent tasks |
| [deploy/env.example](deploy/env.example) | Instance `.env` template (placeholders only) |

## GHL agent

One generic **`ghl`** agent hooks to a single GoHighLevel location via PIT + `locationId` in `.env`. Strategic audit, re-engage lists, and landline handling are **CRM-generic** (not vertical-specific). Optional `--vertical rei` on the audit script enables REI field/pipeline heuristics for instance overlays.

## Instance overlays

Vertical or multi-account customizations (e.g. REI multi-GHL) live under `deploy/examples/instance-overlays/` and on the VPS — not in template defaults.

## License

Proprietary — see repository owner for terms.
