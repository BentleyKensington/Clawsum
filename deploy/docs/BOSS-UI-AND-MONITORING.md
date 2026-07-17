# Boss UI, monitoring, and where work starts

## Three surfaces (use together)

| Surface | URL (via SSH) | Purpose |
|---------|----------------|---------|
| **Boss UI (Paperclip)** | `ssh -L 3100:127.0.0.1:3100 clawsum` → http://localhost:3100 | **Start and track work** — issues, assignees, approvals, heartbeats, costs |
| **Grafana** | `ssh -L 3000:127.0.0.1:3000 clawsum` → http://localhost:3000 | **Metrics** — uptime probes, latency (not chat) |
| **Telegram (@YourTelegramBot)** | Your groups + DM | **Realtime chat** — quick questions, pings, informal delegation |

Paperclip **does not embed Grafana** today. They are complementary: Boss UI = tasks and governance; Grafana = infrastructure graphs. Keep both tabs open or bookmark both tunnels.

**Public domain (no SSH):** see [BOSS-OPS-PORTAL.md](./BOSS-OPS-PORTAL.md) — unified login for Boss UI + OpenClaw Control UI + Grafana. Boss-only subset: [BOSS-UI-PUBLIC-DOMAIN.md](./BOSS-UI-PUBLIC-DOMAIN.md).

---

## Start work in Boss UI (yes — preferred for task lists)

You do **not** need to paste a backlog into admin Telegram first.

### In the UI

1. Open Boss UI (tunnel above).
2. Company **Clawsum** → **Tasks** (or Issues) → **New task**.
3. Set title, description, priority, **assignee** (e.g. Clawsum Coding, Clawsum Data).
4. Save — heartbeats (every ~5 min) wake that agent via OpenClaw or Hermes.

### How to know tasks are processing (monitor progress)

Paperclip does **not** run agents continuously — it **polls on heartbeats** (~5 minutes per agent).

| Signal | Where | What it means |
|--------|--------|----------------|
| **Status → In progress** | Boss UI task board | An agent picked up the issue |
| **Activity feed** | Boss UI (company activity / task history) | Comments, state changes, agent runs |
| **Assignee** | Task detail | Must be a hired agent (e.g. Clawsum Data), not empty |
| **Heartbeat ON** | Agent settings in Boss UI | Required for automatic pickup |
| **Telegram** | Agent’s group or admin DM | Agent may post updates when wired to gateway |
| **CLI snapshot** | VPS script below | Quick counts without clicking UI |

**CLI on VPS:**

```bash
python3 /docker/clawsum/scripts/paperclip-task-status.py
```

Shows per-status counts (`todo`, `in_progress`, `blocked`, `done`), in-progress titles, agent heartbeat on/off, and recent activity.

**If tasks stay in Todo for 15+ minutes:**

1. Confirm assignee is set (e.g. Clawsum Coding, not unassigned).  
2. Run `python3 /docker/clawsum/scripts/enable-paperclip-heartbeats.py` (enables 5 min interval).  
3. Check gateway: `curl -sS http://127.0.0.1:48166/healthz`  
4. OpenClaw auth: `python3 /docker/clawsum/scripts/enforce-llm-codex-first.py` then restart gateway.  
5. Prefer **OpenClaw agents** over **Hermes** for normal tasks (Hermes = long jobs, API key).

**7am report** also lists Paperclip todo / in-progress / blocked samples in Telegram.

### Bulk import from a file (CLI)

```bash
# On VPS — tasks.json example:
# [{"title":"Fix RE scraper","department":"data","priority":"high"},
#  {"title":"GHL pipeline audit","department":"ghl","priority":"medium"}]

python3 /docker/clawsum/scripts/paperclip-create-tasks.py /path/to/tasks.json
```

Then manage/status in Boss UI.

### When to use Telegram admin instead

- Quick triage: “what’s the status?”
- Informal chat, voice-of-Boss directives
- Urgent interrupt outside Paperclip

Admin can still **create Paperclip issues** from chat when you ask; Boss UI is the system of record for tracked work.

---

## Stay involved + autonomous actions

| Control | Where |
|---------|--------|
| **Approvals queue** | Boss UI → Approvals (hires, strategies, gated actions) |
| **Per-agent budget** | Boss UI → agent → monthly budget (100% = auto-pause) |
| **Policy text** | Each agent `SOUL.md` / `ESCALATION.md` (ask-before-send, deploy, spend) |
| **Explicit autonomy** | Issue description: “Boss pre-approved: …” or standing note in admin SOUL |

Tell admin once: *“Approve external sends and prod deploys; internal research and drafts are autonomous.”*

---

## Gmail for admin (forward → archive → triage)

See [GMAIL-ADMIN-SETUP.md](./GMAIL-ADMIN-SETUP.md):

- Dedicated Gmail **`clawsums@gmail.com`** (forward external mail to it)
- `gmail-sync.py` → Postgres `ops.emails` (backfill + every 15 min)
- Optional OpenClaw Gmail watcher for real-time agent processing
- 7am report includes inbox backlog + pending triage

---

## 7:00 AM global report (implemented)

**Schedule:** every day **07:00 America/Chicago**  
**Delivered to:** CS Ops Telegram group (admin) — override with `TELEGRAM_REPORT_CHAT_ID` in `.env` for DM.

**Includes:**

- OpenClaw gateway health  
- Docker container status  
- Paperclip: in-progress, todo, blocked, done samples + recent activity  
- Gmail: last 24h volume, pending triage subjects (when sync enabled)  
- Prometheus target summary (if monitoring profile is up)  
- Disk + recent error tail  

**Scripts:**

| Script | Role |
|--------|------|
| `scripts/daily-global-report.py` | Build + send report |
| `scripts/install-daily-report-cron.sh` | Install cron on VPS |

**Manual test:**

```bash
python3 /docker/clawsum/scripts/daily-global-report.py --dry-run
python3 /docker/clawsum/scripts/daily-global-report.py
```

Reports archived: `/docker/clawsum/data/reports/global-YYYY-MM-DD.md`

---

## Prometheus + Grafana — how data flows

**Yes:** Prometheus collects metrics; Grafana visualizes them. They do **not** store chat, email, or task data.

```text
OpenClaw :48166/healthz  ─┐
Paperclip :3100/api/health ┼─► blackbox exporter (HTTP probe)
                           │
                           ▼
                    Prometheus (scrape + store)
                           │
                           ▼
                    Grafana (dashboards, PromQL)
```

| Tool | Boss uses it for |
|------|------------------|
| **Grafana** | Charts: up/down, probe latency |
| **Prometheus** | Optional debugging (raw targets) |
| **Boss UI** | Tasks, approvals — separate app |
| **7am Telegram report** | Text summary; may include one-line Prometheus target status |

Full Boss URLs and tunnels: [BOSS-ACCESS-GUIDE.md](./BOSS-ACCESS-GUIDE.md).

---

## Prometheus + Grafana

**Enable on VPS:**

```bash
cd /docker/clawsum
docker compose --profile monitoring up -d
```

**Probes (via blackbox exporter):**

- `http://127.0.0.1:48166/healthz` — OpenClaw gateway  
- `http://127.0.0.1:3100/api/health` — Paperclip  

**Grafana:** default login `admin` / password from `GRAFANA_ADMIN_PASSWORD` in `.env`.  
Preloaded dashboard: **Clawsum Health**.

**Not in Boss UI:** open Grafana in a second browser tab. Optional future: Traefik path or link tile in your own ops doc.

---

## Quick SSH bookmarks

```bash
# Boss UI
ssh -L 3100:127.0.0.1:3100 clawsum

# Grafana
ssh -L 3000:127.0.0.1:3000 clawsum

# Prometheus (optional)
ssh -L 9090:127.0.0.1:9090 clawsum
```
