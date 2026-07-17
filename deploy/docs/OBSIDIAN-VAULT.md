# Obsidian vault — Clawsum

Boss-readable knowledge base on the VPS. Agents write domain notes here; **Postgres** stays the system of record for structured data.

---

## Location

| Where | Path |
|-------|------|
| VPS host | `/docker/clawsum/obsidian` |
| OpenClaw container | `/home/node/obsidian` |
| Docker mount | `docker-compose.yml` → `./obsidian:/home/node/obsidian` |

---

## Folder layout (one vault, per agent)

```text
obsidian/
  README.md
  _templates/
  Admin/          ← admin (Reports/, Inbox/)
  Coding/
  Data/
  RealEstate/
  GHL/
  Comms/
  Research/
  Planning/
  Paperclip/
```

Each agent workspace has **`OBSIDIAN.md`** with its folder path and write rules.

---

## Setup on VPS (once)

```bash
python3 /docker/clawsum/scripts/setup-obsidian-vault.py
```

This:

1. Normalizes folder names (removes empty `Ghl` / `Realestate` duplicates)
2. Seeds README, templates, per-folder README, `OBSIDIAN.md` in every workspace
3. Copies `data/reports/global-*.md` → `Admin/Reports/`
4. Installs cron **7:02 AM America/Chicago** (`--sync-only` for daily copy)

Manual sync:

```bash
python3 /docker/clawsum/scripts/setup-obsidian-vault.py --sync-only
```

---

## Open on your PC (pick one)

### Option A — SSHFS (fastest to try)

Mount the VPS folder as a drive; open that path as an Obsidian vault.

### Option B — Git (audit trail)

```bash
cd /docker/clawsum/obsidian
git init
git add .
git commit -m "Clawsum vault seed"
```

Clone on your PC; push/pull via a **private** remote. Do not commit secrets.

### Option C — Syncthing

Install Syncthing on VPS + PC; sync `/docker/clawsum/obsidian` only.

---

## What goes where

| Content | Store |
|---------|--------|
| Gmail archive, triage status | **Postgres** `ops.emails` |
| Deals, CRM rows | **Postgres** (domain DBs) |
| RE comp graph (future) | **ArcadeDB** |
| Boss-readable briefs, ADRs, runbooks | **Obsidian** |
| Session scratch | `workspace-*/notes/` → promote to Obsidian when done |

See [DATA-ARCADEDB-VS-POSTGRES.md](./DATA-ARCADEDB-VS-POSTGRES.md).

---

## Agent usage

On session start (see each `BOOT.md`): read **OBSIDIAN.md** for the vault path.

Examples:

- **research:** finished brief → `Research/Briefs/YYYY-MM-DD-topic.md`
- **planning:** ADR → `Planning/Decisions/adr-NNN-title.md`
- **admin:** triage summary → `Admin/Inbox/` (optional; source of truth remains Postgres)

Telegram: *“Save this to Obsidian under Research as a brief.”*

---

## Cron timeline (Chicago)

| Time | Job |
|------|-----|
| 7:00 | `daily-global-report.py` → Telegram + `data/reports/global-*.md` |
| 7:02 | `sync-obsidian-reports.sh` → `Admin/Reports/` |
| 7:05 | `reminders-notify.py` |

Log: `/docker/clawsum/data/reports/obsidian-sync.log`

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Empty vault | Run `setup-obsidian-vault.sh` |
| Permission errors in container | `chown -R 1000:1000 /docker/clawsum/obsidian` |
| Duplicate folders | Re-run `normalize-obsidian-vault.sh` |
| No reports in Admin/Reports | Run daily report once, then `sync-obsidian-reports.sh` |

---

## Related

- [IMPLEMENTATION-PLAN.md](../../IMPLEMENTATION-PLAN.md) — Phase 4 Obsidian
- [BOSS-UI-AND-MONITORING.md](./BOSS-UI-AND-MONITORING.md) — 7am report content
