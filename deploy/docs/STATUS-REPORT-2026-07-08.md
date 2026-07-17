# Clawsum Status Report

**As of:** July 8, 2026 (repo last touched July 1–2)  
**Reference VPS:** `76.13.97.82` · `/docker/clawsum`  
**Operational mode:** **Boss-paused** since May 26, 2026

---

## Executive Summary

Clawsum is a self-hosted multi-agent operations platform: **9 OpenClaw specialist agents** + **Paperclip** orchestration, backed by Postgres, Obsidian, ArcadeDB, and optional domain packs (GHL CRM, Gmail, etc.). The **platform shell is solid** (Tier 0 complete, Tier 2 partially proved on the live VPS), but **agents are intentionally idle** waiting on Boss input. The repo was recently refactored into a **generic deploy template** ready for GitHub publish, though that publish step itself is still pending.

**Bottom line:** Infrastructure is ahead of automation. The critical path is Boss unblocking the work queue, then finishing Tier 1 operational truth and the remaining Tier 2 automation spine before cloning to additional VPS instances.

---

## Current Operational State

| Area | Status |
|------|--------|
| **Agent execution** | Paused — heartbeats OFF, agents `paused` |
| **Boss work queue** | Waiting on your answers (CLA-41 + per-task comments) |
| **Gmail triage cron** | Disabled during pause |
| **Gmail sync** | Still ingesting (~every 15 min) → `ops.emails` as `pending` |
| **Daily reports + Obsidian sync** | Running |
| **Monitoring** | Prometheus + Grafana up |
| **Template gate** | **Blocks additional VPS clones** until Tier 1 + Tier 2 sign-off |

The May 26 pause was deliberate: heartbeats were picking up `todo` tasks and running long Codex jobs, causing Boss UI timeout errors. With heartbeats OFF, new failures should have stopped; old red runs remain in history.

---

## Most Recent Events & Changes

### May 26 — Full operational pause

- `paperclip-pause-all-work.py` ran: 37 issues → backlog, 33 runs cancelled
- All agents set to `paused`, heartbeats disabled
- Gmail triage cron disabled

### July 1 — Template genericity + access/LLM sprint

- **Template refactor complete:** single generic `ghl` agent, REI/MCO customizations moved to instance overlays, credentials scrubbed from repo
- **OpenClaw upgraded** to `2026.6.10` (after MCO GHL smoke test)
- **MCO REI GHL agent** operational on reference VPS (strategic audit, Telegram, landline tags)
- **OpenRouter escalation scaffold** added: `configure-openrouter-escalation.py`, `openrouter_client.py`, `llm_policy.py`
- **On-demand speech** scaffold: `speech_api.py`
- **Ops portal docs + Traefik script** for unified HTTPS login (Boss UI + OpenClaw Control UI + Grafana)
- **LLM routing policy** documented (`LLM-ROUTING.md`, `OPENROUTER-AND-VOICE.md`)
- **Hermes architecture clarified:** headless via Paperclip → `openclaw_gateway` → session `paperclip:hermes` (not a separate web product)
- `paperclip-analyze-assign-boss.py` updated to suggest `llm:*` labels on tasks

### July 2 — Tier 2 proved on live VPS

- **Redis** — healthy
- **MinIO** — buckets + upload smoke passed
- **LangGraph** — OSS runner live, `/runs/wait` smoke passed (graphs still use stub nodes)
- **Backups** — `backup-platform.sh` + MinIO upload working
- **`verify-tier2.sh` PASSED**
- **Hermes dashboard install scripts** added (`install-hermes-dashboard.sh`) — optional overlay, not the default production path
- **`MASTER-TASK-LIST.md`** consolidated as the canonical backlog tracker

---

## What's Built (by tier)

### Tier 0 — Platform shell ✅

Docker Compose stack, OpenClaw `2026.6.10`, 9 agents + personas, Paperclip protocol v4, Codex-first LLM, bootstrap/verify scripts, Traefik HTTPS, credentials exclusion policy.

### Tier 1 — Operational truth 🔄 (~70%)

| Done | Remaining |
|------|-----------|
| Paperclip ↔ OpenClaw wiring | Boss answers on CLA-41 |
| Gmail sync cron | Gmail **intelligent triage** (production) |
| Daily report + Obsidian crons | Telegram smoke sign-off (manual @mention per group) |
| Boss UI HTTPS | Boss Obsidian desktop access (SSHFS/git) |
| Heartbeat pause/resume runbooks | Promote-to-Obsidian policy in all agent SOUL/WORKFLOWS |
| Admin daily playbook | Resume heartbeats after Boss approval |

### Tier 2 — Automation spine 🔄 (~50%)

| Done | Remaining |
|------|-----------|
| MinIO live + smoke | ArcadeDB schema + ETL (`arcadedb-ingest.py`) |
| LangGraph service + smoke | Wire graphs to **real LLMs** (not stubs) |
| `backup-platform.sh` | Grafana → Telegram alerts |
| `verify-tier2.sh` passed | `install-platform-crons.sh` on VPS |
| Gmail triage + research_brief graph **scaffolds** | Hostinger disk decommission (Phase 8) |

### Tier 3 — Domain packs (per instance, optional)

- MCO REI GHL ✅ live
- AVE/WNN GHL — provisioned, awaiting Boss PIT tokens
- Bright Data scrapers, WhatsApp cutover, voice, 3D viewer, Supabase — all deferred

---

## Architecture (how it works today)

```text
Boss
 ├── Telegram (9 groups + Admin DM)
 ├── Boss UI (Paperclip :3100) — tasks, approvals, heartbeats
 └── Obsidian vault — read reports, strategic knowledge

Paperclip ──heartbeats──► OpenClaw agents (Codex/GPT-5.4)
         └──long jobs──► Clawsum Hermes (headless, same gateway)

Knowledge stores:
  Postgres  → structured data (emails, CRM, ETL)
  Obsidian  → durable notes per agent folder
  ArcadeDB  → graph/vector (container up, no data yet)
  MinIO     → blobs/attachments/backups (live)
```

**Hermes clarification:** There is no separate Hermes web UI in the default stack. "Clawsum Hermes" is a Paperclip assignee that runs headless through the OpenClaw gateway. An optional Nous Hermes dashboard (`:9119`) can be installed later but is not required.

---

## What Remains Next (prioritized)

### 1. Boss unblock (immediate — you)

1. Open **Boss UI** → **CLA-41** and answer clarification questions on tasks you care about
2. Ignore old red heartbeat runs (noise from pre-pause)
3. When ready, tell ops to run:

   ```bash
   python3 /docker/clawsum/scripts/paperclip-resume-work.py --enable-heartbeats
   bash /docker/clawsum/scripts/install-gmail-triage-cron.sh
   ```

   Move approved tasks to `in_progress` **one or two at a time** at first

### 2. Wave 1 — finish operational truth (1–2 weeks)

- [ ] Telegram smoke test — manual @mention in every group (including GHL)
- [ ] Boss Obsidian desktop access — see [BOSS-OBSIDIAN-WINDOWS.md](./BOSS-OBSIDIAN-WINDOWS.md)
- [ ] Gmail intelligent triage production — LLM classify `pending` emails → Paperclip tasks + Obsidian briefs
- [ ] Standardize "promote to Obsidian" policy across all agent personas

### 3. Access & LLM (parallel, VPS-side)

- [ ] Deploy **ops portal** — `setup-ops-portal-traefik.sh` + real DNS
- [ ] Add `OPENROUTER_API_KEY` on VPS + run `configure-openrouter-escalation.py`
- [ ] OpenClaw trusted-proxy patch after portal auth
- [ ] Adopt `llm:cheap|frontier|coding` labels on Paperclip issues (analyze script done; agents reading labels still pending)

### 4. Wave 2 — finish automation spine (2–4 weeks)

- [ ] Wire LangGraph `gmail_triage` + `research_brief` to real LLMs
- [ ] ArcadeDB RE comp schema + first ETL from Postgres
- [ ] Grafana → Telegram alerting (`grafana-telegram-notifier.sh`)
- [ ] `install-platform-crons.sh` on VPS
- [ ] Hostinger decommission / disk cleanup

### 5. Repo publish

- [x] Status report committed and pushed (this file)
- [ ] Confirm no secrets in `git status` before push

### 6. Template gate sign-off (unblocks multi-VPS)

Before cloning to additional production VPS instances:

1. `verify-platform.sh` + Telegram smoke sign-off
2. Gmail triage production
3. MinIO + LangGraph + ArcadeDB ingest all working
4. Grafana alerts wired
5. Bootstrap test on clean VM

---

## Key Doc References

| Doc | Purpose |
|-----|---------|
| [MASTER-TASK-LIST.md](./MASTER-TASK-LIST.md) | Canonical platform backlog (updated July 2) |
| [SETUP-REMAINING.md](./SETUP-REMAINING.md) | Boss queue vs platform checklist; why Boss UI shows errors |
| [PLATFORM-DEPLOY-TEMPLATE.md](./PLATFORM-DEPLOY-TEMPLATE.md) | Multi-VPS template gate |
| [PLATFORM-MASTER-REPORT.md](./PLATFORM-MASTER-REPORT.md) | Full architecture (May 23; some Tier 2 items now done) |
| [../../obsidian/Admin/PLATFORM-TEMPLATE-GATE.md](../../obsidian/Admin/PLATFORM-TEMPLATE-GATE.md) | Short gate status in vault |

---

## Honest Assessment

**Strengths:** The platform migrated off Hostinger, runs a modern OpenClaw stack with Paperclip orchestration, has a clean generic template, and Tier 2 infrastructure (MinIO, LangGraph, backups) is proved on the live VPS.

**Gaps:** The knowledge automation layer is the main missing piece — Gmail sits in Postgres as `pending` without intelligent routing, ArcadeDB is empty, LangGraph graphs are stubs, and agents are paused waiting on Boss.

**The single highest-leverage next step is Boss input on CLA-41**, which unblocks agent execution and lets you validate the full loop (email → triage → Paperclip task → agent deliverable → Obsidian) before investing in the remaining Tier 2 automation.

---

*Generated from codebase and notes analysis on 2026-07-08.*
