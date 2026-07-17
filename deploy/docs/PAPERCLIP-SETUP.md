# Paperclip + Hermes setup (Clawsum)

## Boss task analysis (master list + Gmail)

After Gmail sync or a Boss task dump, run:

```bash
bash /docker/clawsum/scripts/run-boss-task-analysis.sh
```

This will:

1. Triage any pending `ops.emails`
2. Re-split **CLA-1** master list into child tasks (idempotent)
3. **Analyze** each issue (LLM): objective, definition of done, auto-assign specialist
4. Post **Boss clarification questions** as issue comments
5. Create **CLA-41**-style summary issue listing all tasks needing answers

Hold agents until Boss replies:

```bash
python3 /docker/clawsum/scripts/paperclip-hold-for-boss.py
```

Reply on each task in Boss UI (or say *approved as written*), then move to **in_progress**.

### Full pause (Boss not ready — stops Admin run / timeout spam)

```bash
python3 /docker/clawsum/scripts/paperclip-pause-all-work.py
bash /docker/clawsum/scripts/disable-gmail-triage-cron.sh
python3 /docker/clawsum/scripts/paperclip-dedupe-issues.py   # optional cleanup
```

This: pauses all agents, disables heartbeats, **cancels running heartbeat runs**, moves every open issue to **backlog** (unassigned).

Resume: [SETUP-REMAINING.md](./SETUP-REMAINING.md) and `paperclip-resume-work.py`.

## Status (automated)

Run on the VPS:

```bash
python3 /docker/clawsum/scripts/wire-paperclip-clawsum.py
```

This creates the **Clawsum** company, hires 10 agents (9× `openclaw_gateway` + 1× `hermes_local`), and patches gateway auth headers from `OPENCLAW_GATEWAY_TOKEN` in `.env`.

Paperclip uses **host network** so `127.0.0.1:3100` is reachable over SSH tunnel. Gateway URL for adapters: `ws://127.0.0.1:48166` (published OpenClaw port).

## Paperclip UI

```bash
ssh -L 3100:127.0.0.1:3100 clawsum
```

Open http://localhost:3100 — **local_trusted** mode (no bootstrap signup on a private VPS).

Public HTTPS without SSH: [BOSS-UI-PUBLIC-DOMAIN.md](./BOSS-UI-PUBLIC-DOMAIN.md).

## OpenClaw gateway wiring

| Field | Value |
|-------|--------|
| Adapter | **openclaw_gateway** |
| Gateway URL | `ws://127.0.0.1:48166` |
| OpenClaw agent id | `admin`, `coding`, `data`, … (see script) |
| Auth | `Bearer` + `x-openclaw-token` (set by `wire-paperclip-clawsum.py`) |

Instance secret API may 500 in local_trusted; tokens are inlined in each agent’s `adapterConfig` instead.

Pairing (once): from gateway host:

```bash
docker exec clawsum-openclaw-gateway-1 node dist/index.js devices list
docker exec clawsum-openclaw-gateway-1 node dist/index.js devices approve --latest
```

## Agents to hire (mirror Telegram)

| Paperclip agent | Role | OpenClaw agent id |
|-----------------|------|-------------------|
| Clawsum Admin | CEO / liaison | admin |
| Clawsum Coding | Engineer | coding |
| Clawsum Data | Data | data |
| Clawsum RE | Real estate | realestate |
| Clawsum GHL | GHL | ghl |
| Clawsum Comms | Comms | comms |
| Clawsum Research | Research | research |
| Clawsum Planning | Planning | planning |
| Clawsum Paperclip | Orchestrator | paperclip |

## Hermes (long jobs)

```bash
bash /docker/clawsum/scripts/install-hermes-in-paperclip.sh
```

**Clawsum Hermes** uses **`openclaw_gateway`** (not `hermes_local`) so Boss-authorized Hermes jobs bill **ChatGPT Plus / Codex** via the gateway. Hermes heartbeat is **disabled** — assign Hermes only on specific issues.

Optional legacy CLI: `install-hermes-in-paperclip.sh` (not required for Codex path).

Note: Hermes install is **not persisted** across image upgrades — re-run the script after `docker compose pull paperclip`.

## Boss UI workflow (tasks, monitoring, 7am report)

See [BOSS-UI-AND-MONITORING.md](./BOSS-UI-AND-MONITORING.md) — start tasks in Boss UI, Grafana vs Paperclip, daily cron report, bulk task import.

## Troubleshooting

### `protocol mismatch` on heartbeat (Admin / OpenClaw assignees)

OpenClaw **2026.5.20** requires WebSocket **protocol 4**. Published Paperclip `latest` still sends **protocol 3** (`backend vpaperclip min=3 max=3 expected=4` in gateway logs).

**Fix on VPS** (re-run after `docker compose pull paperclip` until upstream ships v4):

```bash
bash /docker/clawsum/scripts/fix-paperclip-openclaw-protocol.sh
```

Then re-open the task in Boss UI → **Heartbeat runs** → log should show connect success, not `protocol mismatch`.

Upstream: [paperclip#6344](https://github.com/paperclipai/paperclip/issues/6344).

### `pairing required` / `device is not approved yet`

Paperclip heartbeats connect from Docker (`172.16.x.x`) with a **new device identity** each time unless configured otherwise. The gateway closes with:

```text
code=1008 reason=pairing required: device is not approved yet (requestId: …)
```

Paperclip then tries `device.pair.approve` but fails with `missing scope: operator.pairing` — a chicken-and-egg loop.

**Clawsum fix (loopback VPS):**

1. Shared **`devicePrivateKeyPem`** on all `openclaw_gateway` agents (same device ID every heartbeat).
2. One-time approve: `python3 /docker/clawsum/scripts/approve-all-paperclip-devices.py`
3. `autoPairOnFirstConnect: false` (no failed self-approve loop)

Apply:

```bash
python3 /docker/clawsum/scripts/paperclip-fix-execution.py --skip-protocol
```

Optional one-time cleanup of old pending requests:

```bash
python3 /docker/clawsum/scripts/approve-all-paperclip-devices.py
```

**Control UI** pairing is separate (your browser) — approve once at https://clawsum.srv.example.com/ if prompted.

### Other

- **Port wrong / connection reset:** `.env` had `PORT=48165` from Hostinger — compose now forces `PORT=3100`.
- **local_trusted bind error:** requires `HOST=127.0.0.1`, not `0.0.0.0`.

## Hermes assignee

See [HERMES-POLICY.md](./HERMES-POLICY.md) — Boss must explicitly assign Hermes; default to **Clawsum Admin** or specialists.
