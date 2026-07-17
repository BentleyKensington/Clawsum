# Boss — how to access every interface

**VPS:** `srv.example.com` (`YOUR_VPS_IP`) · **Stack:** `/docker/clawsum`  
Use SSH config host **`clawsum`** if you have it (`~/.ssh/config`).

---

## Quick reference

| What | How Boss opens it | Auth |
|------|-------------------|------|
| **Telegram (chat)** | Phone/desktop Telegram app | Your Telegram account; bot **@YourTelegramBot** |
| **Boss UI (tasks)** | https://boss.srv.example.com or SSH tunnel → http://localhost:3100 | Traefik basic auth + Paperclip login |
| **OpenClaw Control UI** | https://clawsum.srv.example.com | Traefik basic auth + trusted-proxy (or gateway token) |
| **Grafana (metrics)** | SSH tunnel → http://localhost:3000 | `admin` + `GRAFANA_ADMIN_PASSWORD` |
| **Prometheus (raw metrics)** | SSH tunnel → http://localhost:9090 | None (keep private) |
| **ArcadeDB Studio** | SSH tunnel → http://localhost:2480 | `root` + `ARCADEDB_ROOT_PASSWORD` |
| **Obsidian (knowledge)** | Your PC Obsidian app | [BOSS-OBSIDIAN-WINDOWS.md](./BOSS-OBSIDIAN-WINDOWS.md) — SSHFS `Z:` → VPS vault |
| **Gmail admin inbox** | https://mail.google.com | `clawsums@gmail.com` Google login |
| **7am digest** | Telegram CS Ops group (or DM) | Automatic |

**Live:** Boss UI at **https://boss.srv.example.com** (no SSH tunnel required if DNS resolves).

**Not live yet:** LangGraph UI (`:8123`), unified mission-control.

---

## 1. Telegram — primary realtime interface

**Use for:** quick questions, status, informal orders, voice notes (future).

1. Open Telegram on phone or desktop.
2. Chat with **@YourTelegramBot** (admin DM) or your agent groups (Coding, Data, RE, GHL, etc.).
3. Optional status: send `/status` in admin DM (shows Codex/runtime when configured).

No SSH required. This is **not** the same as Boss UI — Telegram does not show the full task backlog or approvals queue.

---

## 2. Boss UI (Paperclip) — start and track work

**Use for:** tasks, assignees, heartbeats, approvals, agent budgets, cost.

### Public URL (preferred)

**Browser:** https://boss.srv.example.com

Same app as localhost:3100 — tasks, backlog, comments. Agents are **paused** until you finish clarifications and ops re-enables heartbeats.

### SSH tunnel (fallback)

```bash
ssh -L 3100:127.0.0.1:3100 clawsum
```

**Browser:** http://localhost:3100

- Company: **Clawsum**
- Mode: **local_trusted** (no public signup on VPS)

### If the page does not load

```bash
ssh clawsum "curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3100/api/health"
```

Expect `200`. If not:

```bash
ssh clawsum "cd /docker/clawsum && docker compose --profile orchestration up -d paperclip"
```

---

## 3. OpenClaw Control UI — gateway, channels, Gmail (gog), devices

**Use for:** gateway health, Telegram channel config, **Gmail skill (gog)**, device pairing, skills — not Paperclip tasks.

### Public URL (HTTPS)

**Browser:** https://clawsum.srv.example.com/

(Hostname = `clawsum.${TRAEFIK_HOST}` from `.env`.)

### Gateway token

Required on first connect. Token is **`OPENCLAW_GATEWAY_TOKEN`** in `/docker/clawsum/.env` (same value migrated from Hostinger). Paste in Control UI when prompted — **do not commit or paste in chat logs**.

### Approve a new browser/device

If pairing is required, on VPS:

```bash
ssh clawsum "bash /docker/clawsum/scripts/approve-openclaw-device-host.sh"
```

Or device-code flow via `openclaw-cli` (see prior setup notes).

### Health check (optional)

```bash
ssh clawsum "curl -sS http://127.0.0.1:48166/healthz"
```

---

## 4. Grafana — infrastructure charts

**Use for:** “Is the gateway up?” “Is Paperclip healthy?” — **not** agent chat or email triage.

### Does Prometheus “feed” Grafana?

**Yes, for metrics only:**

```text
Services (OpenClaw :48166, Paperclip :3100)
    → blackbox exporter probes HTTP
    → Prometheus scrapes / stores time series
    → Grafana queries Prometheus → dashboards
```

Prometheus does **not** feed Boss UI, Obsidian, ArcadeDB, or Telegram. Grafana does **not** show Gmail bodies, tasks, or LLM conversations.

### Enable monitoring (once per VPS)

```bash
ssh clawsum "cd /docker/clawsum && docker compose --profile monitoring up -d"
```

### Open Grafana

**Terminal:**

```bash
ssh -L 3000:127.0.0.1:3000 clawsum
```

**Browser:** http://localhost:3000

- User: `admin`
- Password: `GRAFANA_ADMIN_PASSWORD` in `/docker/clawsum/.env`

Preloaded dashboard: **Clawsum Health** (probe success, latency).

### Optional: Prometheus UI

```bash
ssh -L 9090:127.0.0.1:9090 clawsum
```

http://localhost:9090 — raw PromQL; Boss usually only needs Grafana.

---

## 5. ArcadeDB Studio — graph / document browser

**Use for:** inspecting vertices, running SQL, debugging ETL — after data is loaded.

**Terminal:**

```bash
ssh -L 2480:127.0.0.1:2480 clawsum
```

**Browser:** http://localhost:2480

- User: `root`
- Password: `ARCADEDB_ROOT_PASSWORD` in `.env`

Database for Clawsum graph work: **`clawsum_graph`** (created by ingest script).

Schema-on-arrival: see [DATA-ARCADEDB-VS-POSTGRES.md](./DATA-ARCADEDB-VS-POSTGRES.md) and `scripts/arcadedb-ingest.py`.

---

## 6. Obsidian — Boss knowledge vault

**Use for:** reading `Admin/`, reports, agent folders; writing Boss notes in `Admin/`.

There is **no web UI** on the VPS. Options:

| Method | Boss experience |
|--------|-----------------|
| **Git** pull/push | Clone `obsidian` repo or subtree |
| **Syncthing** | Sync `/docker/clawsum/obsidian` to PC |
| **SSHFS** | Mount vault as drive; open folder in Obsidian |

Vault path on VPS: `/docker/clawsum/obsidian`  
Layout: [OBSIDIAN-VAULT.md](./OBSIDIAN-VAULT.md)

Daily mirror of global reports: cron `setup-obsidian-vault.py --sync-only` → `Admin/Reports/`.

---

## 7. Gmail — admin inbox (Google, not Clawsum UI)

**Use for:** reading/sending as `clawsums@gmail.com`; forward external mail here.

**Browser:** https://mail.google.com (Google account login).

**Backend sync (no UI):** `gmail-sync.py` → Postgres `ops.emails` every 15 min.  
**OpenClaw Gmail (gog):** configured in **Control UI** §3, not in Boss UI.

Setup: [GMAIL-ADMIN-SETUP.md](./GMAIL-ADMIN-SETUP.md)

---

## 8. Hermes / LangGraph

| System | Access | Status |
|--------|--------|--------|
| **Hermes** | Runs inside Paperclip; results in Boss UI task + Obsidian | ✅ via heartbeats |
| **LangGraph API** | Would be `ssh -L 8123:127.0.0.1:8123` → :8123 | ⬜ compose profile not deployed |

---

## 9. LLM billing — what uses your OpenAI / ChatGPT account?

**Short answer:** Most **OpenClaw agent chat** is designed to use **ChatGPT via Codex OAuth** (subscription sign-in), with **`OPENAI_API_KEY` as fallback** (API billing). **Hermes** and future **LangGraph** jobs use **API keys** from `.env` unless you reconfigure them.

| Workload | Typical provider | Bills what? |
|----------|------------------|-------------|
| Telegram agents (9 specialists) | **openai-codex** OAuth first | **ChatGPT/Codex** subscription when OAuth works |
| Same agents (fallback) | `OPENAI_API_KEY` | **OpenAI API** usage (platform.openai.com) |
| **Hermes** (Paperclip long jobs) | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` in Paperclip compose | **API** accounts |
| **Gmail sync / cron scripts** | No LLM | — |
| **Gmail intelligent triage** (not built) | Will use API or Codex per script config | TBD |
| **LangGraph** (not running) | `DATABASE_URI` + keys in compose when enabled | API when deployed |
| **Grafana / Prometheus** | No LLM | — |

**Important distinctions:**

1. **ChatGPT Plus** and **OpenAI API** are separate products. API key charges are per token on the API dashboard.
2. **Codex OAuth** (`models auth login --provider openai-codex`) ties agent turns to your **ChatGPT sign-in**, not to pasting an API key in Telegram.
3. **`OPENAI_API_KEY` in `.env`** is copied to all agents as `openai:default` — used when Codex OAuth is missing or a tool explicitly uses API profile.
4. Check runtime: Telegram **`/status`** in admin DM; or Control UI model/auth section.

Full setup: [OPENAI-AUTH.md](./OPENAI-AUTH.md)

```bash
# Re-run Codex login if agents say missing API key
ssh -t clawsum "cd /docker/clawsum && docker compose run --rm openclaw-cli models auth login --provider openai-codex --device-code"
ssh clawsum "python3 /docker/clawsum/scripts/setup-openai-codex-auth.py"
ssh clawsum "cd /docker/clawsum && docker compose restart openclaw-gateway"
```

---

## 10. Recommended Boss daily routine

1. **Telegram** — overnight pings and quick replies.  
2. **Boss UI** (tunnel) — review Tasks, Approvals, blocked work.  
3. **Gmail** — human triage; compare with pending count in 7am report.  
4. **Obsidian** — `Admin/Reports/` and `Admin/` notes.  
5. **Grafana** (weekly or when something feels down) — health probes.  
6. **Control UI** — only when changing channels, Gmail, or devices.

---

## 11. All SSH tunnels in one session (optional)

```bash
ssh -L 3100:127.0.0.1:3100 \
    -L 3000:127.0.0.1:3000 \
    -L 9090:127.0.0.1:9090 \
    -L 2480:127.0.0.1:2480 \
    clawsum
```

Then open:

- http://localhost:3100 — Boss UI  
- http://localhost:3000 — Grafana  
- http://localhost:9090 — Prometheus  
- http://localhost:2480 — ArcadeDB  

Control UI stays on **https://clawsum.srv.example.com/** (no tunnel).

---

## Related docs

| Doc | Topic |
|-----|--------|
| [BOSS-UI-AND-MONITORING.md](./BOSS-UI-AND-MONITORING.md) | Boss UI vs Grafana, 7am report |
| [BOSS-UI-PUBLIC-DOMAIN.md](./BOSS-UI-PUBLIC-DOMAIN.md) | Public HTTPS Boss UI |
| [OPENAI-AUTH.md](./OPENAI-AUTH.md) | Codex vs API key |
| [PLATFORM-MASTER-REPORT.md](./PLATFORM-MASTER-REPORT.md) | Full architecture |
