# LAST_SESSION.md — handoff

_Updated 2026-08-11. Hermes should rewrite this on Wrap session. If this date is old, say so._

## Summary

Ops kept running on OpenClaw + Paperclip. Boss UI Graphify now paints three side-by-side 3D decks (Arcade / Obsidian / Hermes). Hermes messaging gateway was dead since 29 Jul (not a service); keepalive cron + systemd now restart it. Gmail OAuth (`clawsums@gmail.com`) broke on 7-day Testing tokens; re-authed 11 Aug. Morning reports were firing at 02:30 CDT because this VPS ignores `CRON_TZ`; GHL + content-factory are now Chicago-gated to 07:30.

## Done recently

- Graphify: three panes side-by-side; canvas 3D (CDN/WebGL overlay was blanking the draw)
- Hermes gateway keepalive (`/etc/cron.d/clawsum-hermes-dashboard` + `clawsum-hermes-runtime.service`)
- `config.yaml` snapshot/restore (`hermes-config-safe.py`) so a bad write cannot stick
- Cron: `run-at-chicago.sh` for GHL send/generate, content-factory, nightly backup
- Gmail: new refresh token; sync OK (13 messages / 6 pending triage at re-auth)

## Open for next session

1. Publish the Google OAuth app to Production (or keep re-authing every 7 days while Testing)
2. Confirm which Google account *owns* the Cloud project (project number `33728292336`) — mailbox is `clawsums@gmail.com`, owner may be a different login
3. Gerald: triage needs_boss inbox + pending approvals
4. `arcade.clawsum.com` public DNS A record still missing
5. Heartbeats stay off until RESUME-POLICY / CLA-41

## Risks

- Gmail token dies again in 7 days if the OAuth app stays in Testing
- Ubuntu cron ignores `CRON_TZ` — any new “7:30” job must use `run-at-chicago.sh`
- LAST_SESSION only updates on Wrap session (or a manual rewrite). Skipping wrap leaves this file frozen.
