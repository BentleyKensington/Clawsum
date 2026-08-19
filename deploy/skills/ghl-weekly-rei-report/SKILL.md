---
name: ghl-weekly-rei-report
description: Nightly REI ops report for GHL MCO and Avenou (AVE). Audit at 22:00 Chicago; digest sent 07:30. Use when Boss asks for daily/weekly GHL report or cron install.
agents: [ghl, admin]
cells: [wnn-client]
tier_autonomous: 1
credentials: [GHL_*, POSTGRES_*]
approval_actions: [send_sms, send_email, bulk_contact_update]
---

# GHL daily REI report (MCO + Avenou)

## Cron

```bash
bash /docker/clawsum/scripts/install-ghl-weekly-report-cron.sh
# 22:00 America/Chicago — generate (audit, no send)
# 07:30 America/Chicago — send digest
```

## Manual

```bash
python3 /docker/clawsum/scripts/ghl-weekly-report.py --slugs mco-rei,ave-rei --audit --use-llm
python3 /docker/clawsum/scripts/ghl-weekly-report.py --slugs mco-rei --no-audit --dry-run
```

## Agent behavior

1. Seed/read `KNOWLEDGE-REI.md` for wholesaling advice and scripts.
2. After cron: summarize from `WEEKLY.md` (exact path read — no search).
3. Re-engage detail still from `REENGAGE.md`.
4. Sends remain Tier 2.
