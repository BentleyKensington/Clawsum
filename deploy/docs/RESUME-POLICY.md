# Resume policy — unpause agents safely

**Status:** Platform remains **Boss-paused** until you complete the checklist below.  
**Goal:** Avoid the May 26 failure mode (heartbeats picking `todo` → stacked Codex runs → Boss UI timeouts).

---

## Rules (locked)

1. **Heartbeats stay OFF** until CLA-41 (and any tasks you care about) have Boss answers.
2. **`todo` means “agent may work”** in Paperclip — not “waiting on Boss.” Park unfinished clarification in **`backlog`**.
3. Resume **one or two** issues to `todo` / `in_progress` first — never re-open the whole backlog at once.
4. **Clawsum Hermes** assignee stays heartbeat-off; only assign with `Boss authorized Hermes: yes`.
5. **Gmail triage cron** stays off until heartbeats are stable for ≥24h (sync may keep running).
6. Ignore **old red** Admin/heartbeat runs in history — they are pre-pause noise.

---

## Checklist before resume

- [ ] Boss UI open (`https://boss…` or tunnel `:3100`)
- [ ] CLA-41 + priority task comments answered (or “approved as written”)
- [ ] Hermes UI available if using browser-first chat ([CEO-COCKPIT.md](./CEO-COCKPIT.md))
- [ ] Confirm no secrets in Telegram/Discord logs
- [ ] Daily report cron verified at **07:00 America/Chicago** (not 02:00) — see below

---

## Resume commands (VPS)

```bash
cd /docker/clawsum

# 1) Unpause agent statuses only (heartbeats still OFF)
python3 scripts/paperclip-resume-work.py

# 2) Move 1–2 approved issues to todo / in_progress in Boss UI

# 3) Enable heartbeats when ready
python3 scripts/paperclip-resume-work.py --enable-heartbeats
# equivalent: python3 scripts/enable-paperclip-heartbeats.py

# 4) After 24h stable — optional Gmail triage
bash scripts/install-gmail-triage-cron.sh
```

### Emergency re-pause

```bash
python3 scripts/paperclip-pause-all-work.py
bash scripts/disable-gmail-triage-cron.sh
```

---

## Daily Telegram time (7:00 AM CST/CDT)

**Symptom:** Reports arriving ~**2:00 AM** Chicago time.  
**Cause:** Cron `0 7 * * *` evaluated in **UTC** on the VPS; `TZ=America/Chicago` on the command only affects the Python process, **not** the schedule. 07:00 UTC ≈ 02:00 CDT.

**Fix on VPS** (re-run installers — they now set `CRON_TZ=America/Chicago`):

```bash
cd /docker/clawsum
bash scripts/install-daily-report-cron.sh
bash scripts/install-reminders-cron.sh
bash scripts/install-obsidian-sync-cron.sh
crontab -l | head -20   # must show CRON_TZ=America/Chicago and 0 7 for daily report
```

Manual one-shot test:

```bash
python3 scripts/daily-global-report.py --dry-run
python3 scripts/daily-global-report.py
```

---

## Related

- [PAPERCLIP-SETUP.md](./PAPERCLIP-SETUP.md) — pause / analyze / CLA-41
- [PAPERCLIP-OVERWATCH.md](./PAPERCLIP-OVERWATCH.md) — Phase 3 governance
- [SETUP-REMAINING.md](./SETUP-REMAINING.md) — why UI shows timeouts
- [Admin-Runbooks/daily-boss-routine.md](./Admin-Runbooks/daily-boss-routine.md)
