# Platform template gate — multi-VPS deploy

**Rule:** Do not clone Clawsum to additional unrelated VPS instances until **Tier 1 + Tier 2** are complete on the reference server.

## Status (2026-07-01)

| Tier | What | Status |
|------|------|--------|
| **0** | Shell (compose, bootstrap, env.example) | ✅ |
| **1** | Operational truth (Telegram, Gmail, Paperclip, smoke) | 🔄 |
| **2** | Automation spine (MinIO, LangGraph, ArcadeDB, alerts) | 🔄 compose + stubs in repo |
| **3** | Domain packs (optional per instance) | Per deploy |
| **Generic** | Single `ghl`, unbranded repo | ✅ see `deploy/docs/CREDENTIALS-EXCLUSION.md` |

**Persona OS:** ✅ `deploy/docs/AI-PERSONA-OS.md` — seed via `seed-persona-os.sh` + `provision-ghl-accounts.py`

## Rule

Template repo = generic. Reference VPS customizations (MCO/AVE/WNN GHL, REI playbook) = **instance overlay**, not what ships on clone.

## Finish order (reference VPS first)

1. `verify-platform.sh` + Telegram smoke sign-off  
2. Gmail triage production  
3. MinIO + LangGraph + ArcadeDB ingest  
4. Grafana → Telegram alerts  
5. Bootstrap test on clean VM → **template sign-off**

## Full spec

`/docker/clawsum/deploy/docs/PLATFORM-DEPLOY-TEMPLATE.md`

## Greenfield new VPS

```bash
cp deploy/env.example .env   # fill secrets
bash deploy/scripts/bootstrap-new-vps.sh
bash deploy/scripts/verify-platform.sh
```

Instance config only: `.env`, Telegram groups, optional GHL PITs — never commit secrets to git.
