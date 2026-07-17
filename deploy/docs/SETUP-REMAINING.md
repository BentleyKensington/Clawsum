# Clawsum setup — what’s done vs what’s left

**Last updated:** 2026-07-02  
**Master task list (all items):** [MASTER-TASK-LIST.md](./MASTER-TASK-LIST.md)  
**Boss UI:** https://boss.srv.example.com or SSH tunnel → http://localhost:3100  
**Full roadmap:** [PLATFORM-MASTER-REPORT.md](./PLATFORM-MASTER-REPORT.md) §14–15  
**Multi-VPS template gate:** [PLATFORM-DEPLOY-TEMPLATE.md](./PLATFORM-DEPLOY-TEMPLATE.md)

---

## Two different “lists” (don’t mix them up)

| List | What it is | Where |
|------|------------|--------|
| **Boss work queue** | Your business tasks (Gmail, CLA-1 master list) — need *your* answers before agents execute | Boss UI → **CLA-41** + each task’s comments |
| **Platform setup checklist** | Infrastructure/features still to build so Clawsum is “fully set up” | **This file** + [PLATFORM-MASTER-REPORT.md](./PLATFORM-MASTER-REPORT.md) §15 |

Analyzing Gmail/master-list items does **not** finish platform setup. It only prepares *your* backlog with assignees and questions.

---

## What is “running” if tasks wait for Boss?

These run **whether or not** you replied:

| Process | Schedule | What you see in Boss UI |
|---------|----------|-------------------------|
| **Paperclip heartbeats** | Every **5 min** per agent (when ON) | “Admin run”, heartbeat logs, timeouts |
| **Gmail sync** | Cron ~15 min | New emails → more tasks if triage runs |
| **Grafana/Prometheus** | Always | Metrics (not task errors) |
| **OpenClaw gateway** | Always | Telegram when you message bots |

**Heartbeats** = Paperclip waking each agent to “check for work.” If tasks are `todo` or `in_progress`, the agent tries to run Codex on them → long runs → **“timed out”** / **blocked** when they exceed `waitTimeoutMs` (~5 min) or fail.

**“Hold until Boss replies”** mistakenly set status to **`todo`**. In Paperclip, **`todo` means “ready for an agent to work”** — not “waiting on Boss.” Heartbeats treat `todo` + assignee as a work queue.

Paperclip has **no** status called `pending` or `on hold`. Only: `backlog`, `todo`, `in_progress`, `in_review`, `blocked`, `done`, `cancelled`.

| Status | What it means | Heartbeat (when ON) |
|--------|----------------|---------------------|
| **backlog** | Not started / parked | May still pick up on timer wake |
| **todo** | Ready to work | **Yes — primary pickup status** |
| **in_progress** | Agent is working | **Yes — continues / retries** |
| **blocked** | Failed or stuck | Recovery may retry |

So: **Boss comments ≠ pause.** Only **heartbeats OFF** (done on VPS) or Paperclip **tree-hold pause** truly stops runs.

**Fix:** heartbeats are **OFF** until you reply and ask to resume:

```bash
python3 /docker/clawsum/scripts/disable-paperclip-heartbeats.py   # pause
python3 /docker/clawsum/scripts/enable-paperclip-heartbeats.py    # resume later
```

---

## Why Boss UI shows errors (e.g. Admin run timed out)

Typical causes on this stack:

1. **Too many tasks `in_progress` at once** — heartbeats stacked; Admin ran many CLA items in parallel.
2. **Codex run longer than adapter timeout** — heartbeat marked failed / blocked.
3. **Earlier pairing/protocol errors** — now fixed; old runs still visible in history.
4. **Tasks assigned to Admin** during recovery — specialist work ran as Admin and overloaded one session.

With heartbeats **OFF**, new timeout errors should **stop**. Old failed runs remain in the log until you clear or ignore them.

---

## Platform setup — honest status

### Done (operational baseline)

- [x] VPS stack: OpenClaw, Postgres, Paperclip, monitoring
- [x] 9 Telegram agents + personas
- [x] Codex-first LLM on agents
- [x] Paperclip ↔ OpenClaw execution path (pairing + protocol v4)
- [x] Gmail ingest + triage scripts
- [x] Master list split (CLA-1 → children) + analyze/assign/Boss questions (CLA-2…)
- [x] Hermes policy (heartbeat off, Boss-authorized only)

### Not done — required for “fully set up” **and template-complete**

> **Template gate:** Finish Wave 1 + Wave 2 on the reference VPS before deploying additional unrelated instances. See [PLATFORM-DEPLOY-TEMPLATE.md](./PLATFORM-DEPLOY-TEMPLATE.md).

#### Tier 0 — greenfield bootstrap

- [x] `bootstrap-new-vps.sh` — greenfield install orchestrator
- [x] `env.example` — master instance overlay template
- [x] `verify-platform.sh` — single verify gate (Tier 2 checks show PENDING until built)

#### Wave 1 — operational truth

- [ ] **Boss answers** on CLA-41 / per-task clarification comments
- [x] **Heartbeats policy** — OFF + agents `paused` (`paperclip-pause-all-work.py`)
- [x] **Dedupe/clean queue** — `paperclip-dedupe-issues.py` (productivity + duplicate titles)
- [x] **Gmail triage cron** — disabled during Boss pause (`disable-gmail-triage-cron.sh`)
- [x] **Admin daily playbook** — [Admin-Runbooks/daily-boss-routine.md](./Admin-Runbooks/daily-boss-routine.md)
- [x] **Boss UI HTTPS** — https://boss.srv.example.com (`setup-boss-ui-traefik.sh`)
- [ ] **Telegram smoke test** — script enhanced; manual @mention in each group (incl. CS GHL)
- [ ] **Gmail triage** — finish policy; cron disabled during Boss pause (`disable-gmail-triage-cron.sh`)
- [ ] **Boss Obsidian desktop access** — *bookmarked* — [BOSS-OBSIDIAN-WINDOWS.md](./BOSS-OBSIDIAN-WINDOWS.md)
- [ ] **Boss Paperclip backlog replies** — *bookmarked* — CLA-41 + per-task comments
- [x] **GHL multi-account agents** — MCO REI live (strategic audit, Telegram, landline tags); AVE/WNN await PIT — [GHL-MULTI-ACCOUNT-PLAN.md](./GHL-MULTI-ACCOUNT-PLAN.md), [REI-GHL-AGENT-PLAYBOOK.md](../obsidian/GHL/REI-GHL-AGENT-PLAYBOOK.md)
- [x] **OpenClaw + Paperclip version pin** — OpenClaw `2026.6.10`; Paperclip `latest` (digest on VPS) — `upgrade-platform-versions.sh`

#### Wave 2 — automation spine

- [x] **MinIO** — live on reference VPS; `verify-tier2.sh` passed
- [x] **LangGraph** — OSS runner live; graphs smoke-tested (stub nodes — wire to production LLM later)
- [x] **Backup platform** — `backup-platform.sh` + MinIO upload
- [ ] **ArcadeDB RE comps + ETL**
- [ ] **Grafana → Telegram alerts**
- [ ] **Platform crons** — `install-platform-crons.sh`
- [ ] Bright Data scrapers
- [ ] Hostinger decommission (Phase 8)

#### Access & LLM (new)
- [ ] **Ops portal** — `setup-ops-portal-traefik.sh` + DNS
- [ ] **OpenRouter on VPS** — `OPENROUTER_API_KEY` + `configure-openrouter-escalation.py`
- [ ] **LLM task labels** — `llm:cheap|frontier|coding` convention — [LLM-ROUTING.md](./LLM-ROUTING.md)
- [ ] **Hermes native dashboard** — optional; not required for headless path

- [ ] Voice, 3D viewer, Supabase (deferred)

See [PLATFORM-MASTER-REPORT.md](./PLATFORM-MASTER-REPORT.md) for full detail and MinIO/Supabase guidance.

---

## What you should do now

1. **Boss UI** — open **CLA-41**; answer questions on tasks you care about (ignore noise).
2. **Ignore old red runs** in heartbeat history if heartbeats are now OFF.
3. When ready for agents to work: tell ops to run `enable-paperclip-heartbeats.py` and move approved tasks to **in_progress** (one or two at a time at first).

---

## Quick commands (VPS)

```bash
cd /docker/clawsum
python3 scripts/paperclip-task-status.py

# Full pause (backlog all, cancel runs, pause agents, heartbeats OFF)
python3 scripts/paperclip-pause-all-work.py
bash scripts/disable-gmail-triage-cron.sh

# Cleanup duplicates / productivity-review noise
python3 scripts/paperclip-dedupe-issues.py

# Resume after Boss updated tasks
python3 scripts/paperclip-resume-work.py
python3 scripts/paperclip-resume-work.py --enable-heartbeats
bash scripts/install-gmail-triage-cron.sh
```

**Last full pause:** 2026-05-26 — all agents `paused`, heartbeats OFF, 37 issues → backlog, 33 runs cancelled.
