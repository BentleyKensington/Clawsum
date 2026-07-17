# Boss daily routine — Clawsum

**Boss UI:** `ssh -L 3100:127.0.0.1:3100 clawsum` → http://localhost:3100  
**Control UI (OpenClaw):** https://clawsum.srv.example.com/

## Morning (15 min)

1. **Boss UI** — open **CLA-41** (clarification checklist) or filter **backlog**.
2. On each task you care about: read **Boss — clarification needed** comment → reply with deadline, deliverable, constraints.
3. **Telegram** — check **Admin** DM / group for overnight agent messages.
4. **Grafana** (optional): http://localhost:3000 via tunnel — stack health only.

## Email

- Gmail sync runs every 15 min (`gmail-sync.py`).
- Triage cron may be **off** while queue is paused — no new auto-tasks until re-enabled.
- Pending mail: query Postgres `ops.emails` where `processing_status = 'pending'`.

## Delegating work

While automation is paused:

- Do **not** expect agents to execute backlog items.
- When ready: ops runs `paperclip-resume-work.py --enable-heartbeats` and moves **approved** tasks `backlog` → `todo` → `in_progress` (1–2 at a time).

## End of day

- Skim Paperclip **backlog** — cancel noise, keep real work.
- Check `Admin/Reports/` in Obsidian vault (when synced) for daily report output.

## Pause / resume (VPS)

```bash
# Full pause (Boss not ready)
python3 /docker/clawsum/scripts/paperclip-pause-all-work.py
bash /docker/clawsum/scripts/disable-gmail-triage-cron.sh

# Resume (after Boss updated tasks)
python3 /docker/clawsum/scripts/paperclip-resume-work.py --enable-heartbeats
bash /docker/clawsum/scripts/install-gmail-triage-cron.sh
```

See [SETUP-REMAINING.md](../SETUP-REMAINING.md) and [BOSS-ACCESS-GUIDE.md](../BOSS-ACCESS-GUIDE.md).
