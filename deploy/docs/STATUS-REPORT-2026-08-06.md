# Clawsum Status Report

**As of:** August 6, 2026 (America/Chicago evening Aug 5)  
**Covers:** changes since [STATUS-REPORT-2026-07-08.md](./STATUS-REPORT-2026-07-08.md)  
**Reference VPS:** `76.13.97.82` · `/docker/clawsum`  
**Related topical docs:** [MEDIA-PRODUCTION-STUDIO.md](./MEDIA-PRODUCTION-STUDIO.md), [LOCAL-STACK-PLAN.md](./LOCAL-STACK-PLAN.md)

---

## Executive summary

Since the July 8 report, Clawsum moved from **Boss-paused / template-focused** into a live ops sprint: Media Production Studio was designed and wired into authority, Avenou GHL archive closeout was unblocked via a Paperclip agent API proxy, Media Phase 0 landed on the VPS, and a Discord/Telegram outage (caused by config that force-disabled chat plugins) was fixed with **automatic missed-message replay** after future outages.

**Bottom line:** Chat is back online; Paperclip agent closeouts work through `:3102`; Media agent + Phase 0 tooling exist on the VPS; local GPU stack / local LLM remain **explicitly deferred**.

---

## Timeline (high signal)

| When | What |
|------|------|
| Jul → early Aug | Ops portal, Discord HQ, Hermes cockpit, Authelia, monitoring, Gmail pipeline work continued in repo/docs |
| **Aug 4** | Media Production Studio advisory → doc + skills + `media` agent authority |
| **Aug 4–5** | Avenou / CLA-59 stuck on Authelia 302; Paperclip `0.0.0.0` bind rejected by `local_trusted` |
| **Aug 5** | Host proxy `:3102` → loopback `:3100`; CLA-59 closed; Media Phase 0 tools + CLA-62 |
| **Aug 5 night** | Discord + Telegram non-responsive — plugins force-disabled by `configure-openclaw.py` |
| **Aug 5–6** | Channels re-enabled; one Discord `Status` replayed; **auto outage-replay cron** installed |

---

## 1. Media Production Studio

### Design (locked)

- **Control plane:** Hermes proposes → Paperclip assigns → OpenClaw `media` executes → Gerald for Tier 2 publish  
- **Locked tools:** FFmpeg/FFprobe, auto-editor, yt-dlp, Faster Whisper, Demucs/UVR, DaVinci Resolve Studio  
- **Options:** Cut/Storm, Velorn+ComfyUI, AudioCraft, local TTS, Flux thumbs; CapCut/Opus fallback only  
- **Google Photos:** Picker / local mirror only (no full-library API sync)  
- **Deferred by Boss:** local stack / local LLM (see [LOCAL-STACK-PLAN.md](./LOCAL-STACK-PLAN.md))

### Repo wiring

| Area | Change |
|------|--------|
| [AUTHORITY.md](../skills/AUTHORITY.md) | Agent **Clawsum Media** (`media`), cell `media-production` |
| [CATALOG.md](../skills/CATALOG.md) | Skills: `media-trends-brief`, `media-ingest-watch`, `media-transcribe`, `media-package-seo`, `media-shorts-factory`, `media-longform-resolve`, `media-generative-broll`, `media-publish` |
| Skills dirs | `deploy/skills/media-*/` |
| OpenClaw / Paperclip | `configure-openclaw.py`, `seed-persona-os.sh`, `wire-paperclip-clawsum.py`, cockpit `authority.json`, Hermes `SOUL.md` standing order |
| Docs | [MEDIA-PRODUCTION-STUDIO.md](./MEDIA-PRODUCTION-STUDIO.md) |

### VPS Phase 0 (live)

- FFmpeg + yt-dlp installed on host  
- Inbox path: `/docker/clawsum/data/media/inbox`  
- Scripts: `media-ingest.py`, `provision-media-agent.sh`, `setup-media-phase0.sh`, `create-media-phase0-issue.py`  
- Paperclip Media Phase 0 issue **CLA-62** created  
- Still incremental: MinIO `clawsum-media` bucket hardening, `WHISPER_URL`, real ingest `--apply`, Resolve/Comfy later phases

---

## 2. Avenou / GHL archive (CLA-59)

### Problem

Successful agent runs could not close issues: **`missing_disposition`**. Agents called `https://paperclip.clawsum.com/api` and hit **Authelia 302**. Binding Paperclip to `0.0.0.0` broke `local_trusted` (Paperclip refused to stay up).

### Fix

| Piece | Detail |
|-------|--------|
| Paperclip bind | Keep **`127.0.0.1:3100`** |
| Agent proxy | Host service **`clawsum-paperclip-agent-proxy`** on **`0.0.0.0:3102`** → rewrite Host → `127.0.0.1:3100` |
| Gateway env | `PAPERCLIP_API_URL=http://host.docker.internal:3102/api` |
| Scripts | `fix-paperclip-agent-proxy.sh`, `fix-cla59-avenou-closeout.py` |

### Outcome

- **CLA-59 → done** (3 work-products registered)  
- CLA-50…58 cancelled as duplicates  
- Smoke **CLA-61** OK  

**Rule:** OpenClaw agents must use local agent API (`:3102`), never the public Paperclip hostname.

---

## 3. Discord / Telegram outage and recovery

### Root cause

`configure-openclaw.py` (Media provision path, ~Aug 5 ~03:00 UTC) **force-disabled** `plugins.entries.discord` / `telegram` (and telegram channel). Gateway stayed “healthy”; chat was dead.

### Immediate fix

- Re-enabled Discord + Telegram live (`_fix-enable-discord-telegram.py` / `_run-enable-channels.sh`)  
- Gateway logs showed `@Clawsum` (Discord) and `@Clawsumsbot` (Telegram) starting again  
- **Repo fix:** `configure-openclaw.py` no longer force-disables Discord/Telegram (keeps them on; WhatsApp stays off)

### Missed-message replay (one-shot)

- Script: `replay-missed-chat.py`  
- Discord history since outage: unreplied **`Status`** (sent ~12 min before bot returned) → replayed successfully  
- Telegram: Bot API has no history; pending updates empty; reconnect polling already delivered post-recovery traffic  
- DMs: none

---

## 4. Automatic replay after any outage (new)

Installed so recovery is not manual next time.

| Component | Path / unit |
|-----------|-------------|
| Watcher | `scripts/chat-outage-watch.py` |
| Replay | `scripts/replay-missed-chat.py` (dedupe + skip already-answered) |
| Install | `scripts/install-chat-outage-replay.sh` |
| Cron | `/etc/cron.d/clawsum-chat-outage-replay` (every minute) |
| State | `/docker/clawsum/data/chat-replay/outage-state.json` |
| Replayed IDs | `/docker/clawsum/data/chat-replay/replayed-ids.json` |
| Log | `/var/log/clawsum-chat-outage-watch.log` |

**Detects outage when:** gateway container down, or Discord/Telegram channel/plugin disabled in `openclaw.json`.

**On recovery (≥90s down):** Discord history replay for the outage window (60s pre-buffer, 24h max lookback). Telegram left to OpenClaw’s own `getUpdates` polling (calling it from the watcher would steal updates).

**Also wired into:** `bootstrap-new-vps.sh`, `install-monitoring.sh`.

---

## 5. Notable script / config inventory (this sprint)

| Script / unit | Role |
|---------------|------|
| `fix-paperclip-agent-proxy.sh` | systemd proxy `:3102` → `:3100` |
| `fix-cla59-avenou-closeout.py` | Close Avenou archive issue via local API |
| `provision-media-agent.sh` / `setup-media-phase0.sh` / `media-ingest.py` | Media agent + Phase 0 |
| `configure-openclaw.py` | Includes `media`; **does not** kill Discord/Telegram |
| `_fix-enable-discord-telegram.py` | Emergency channel re-enable |
| `replay-missed-chat.py` | Manual or triggered Discord replay |
| `chat-outage-watch.py` | Outage → recovery → auto-replay |
| `install-chat-outage-replay.sh` | Cron + state seed |

---

## Current operational state

| Area | Status |
|------|--------|
| **Discord / Telegram** | Online after re-enable; auto-replay armed |
| **Paperclip agent API** | Via `:3102` proxy; public URL still Authelia-gated (correct for humans) |
| **Avenou CLA-59** | Done |
| **Media agent** | Defined + Phase 0 started (CLA-62); tools partial |
| **Local stack / local LLM** | Deferred |
| **Heartbeats / full queue resume** | Still gated by CLA-41 / [RESUME-POLICY.md](./RESUME-POLICY.md) unless Boss directed otherwise |
| **Gmail triage cron** | Was disabled under pause; confirm before re-enabling |

---

## Open / next

1. Confirm unanswered Discord traffic after recovery (e.g. Origin agent note) if still needed  
2. Media Phase 0: ingest `--apply`, MinIO `clawsum-media`, Whisper endpoint  
3. YouTube publish OAuth (Tier 2) when ready  
4. Resolve / Comfy phases 3–4 on GPU host  
5. Local stack / LLM when Boss un-defers  
6. Consider rotating Telegram bot token if it was ever printed in diagnostics  
7. Do **not** re-run old `configure-openclaw` without the fixed version (would disable chat again)

---

## Doc map

| Doc | Role |
|-----|------|
| This file | Sprint status since July 8 report |
| [MEDIA-PRODUCTION-STUDIO.md](./MEDIA-PRODUCTION-STUDIO.md) | Media architecture + phases |
| [LOCAL-STACK-PLAN.md](./LOCAL-STACK-PLAN.md) | Deferred local GPU/LLM plan |
| [AUTHORITY.md](../skills/AUTHORITY.md) / [CATALOG.md](../skills/CATALOG.md) | Agents, skills, tiers |
| [MASTER-TASK-LIST.md](./MASTER-TASK-LIST.md) | Broader backlog (may lag this sprint) |
