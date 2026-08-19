# Media Production Studio

**Status:** Authority + skills wired (Aug 2026). Runtime scripts Phase 0+ incremental.  
**Owner agent:** OpenClaw `media` (**Clawsum Media**)  
**Orchestration:** Hermes proposes → Paperclip assigns → OpenClaw executes  

Related: [AUTHORITY.md](../skills/AUTHORITY.md), [CATALOG.md](../skills/CATALOG.md), [LOCAL-STACK-PLAN.md](./LOCAL-STACK-PLAN.md)

---

## Control plane (answer)

| Layer | Who | Does |
|-------|-----|------|
| **Hermes / Clawsum UI** | `hermes` | Boss conversation; clarifies intent; creates Paperclip work; does **not** run FFmpeg |
| **Paperclip** | `paperclip` / Admin | Board truth; assignee = **Clawsum Media**; risk notes |
| **OpenClaw** | `media` | Executes media skills with `exec` on GPU host; owns MinIO writes for media |
| **Gerald** | human | Tier 2 publish / paid spend; Tier 3 wipe/rotate |

```text
Boss ↔ Hermes
        │  Paperclip issue (cell=media-production, assignee=media)
        ▼
   OpenClaw agent `media`
        │  Tier 0–1: ingest → Whisper → package → FFmpeg / Resolve / Comfy drafts
        ▼
   ops.approvals (Tier 2) → Gerald → media-publish (YouTube / social APIs)
```

---

## Locked core tooling

| Tool | Role |
|------|------|
| **FFmpeg / FFprobe** | Cut, crop, captions, NVENC, loudnorm, thumbs |
| **auto-editor** | Silence / dead-air cleanup |
| **yt-dlp** | URL / YouTube fetch |
| **Faster Whisper** | Transcripts + timestamps |
| **Demucs / UVR** | Audio stems / cleanup |
| **DaVinci Resolve Studio** | Flagship long-form (+ dvr MCP) |
| **Hermes + Paperclip + OpenClaw** | Orchestration |

## Recommended options

Cut/Storm (UI) · Velorn + ComfyUI · AudioCraft/MusicGen · XTTS/F5/Sesame · Flux/SDXL thumbs · OpenReelio (watch) · Opus/CapCut (fallback only)

---

## Phases → skills

| Phase | Skill | Auto ≤ |
|-------|-------|--------|
| Trends | `media-trends-brief` | 0 |
| 0 Ingest | `media-ingest-watch` | 1 |
| 0 Transcribe | `media-transcribe` | 1 |
| 1 Package | `media-package-seo` | 1 |
| 2 Shorts | `media-shorts-factory` | 1 |
| 3 Long-form | `media-longform-resolve` | 1 |
| 4 Generative | `media-generative-broll` | 1 (paid=2) |
| Publish | `media-publish` | draft 1 / publish **2** |

---

## Cells & credentials

- **Cell:** `media-production` (+ `hardware-local-ai` for GPU)
- **Creds:** `MINIO_*`, `POSTGRES_*`, `FFMPEG_BIN`, `WHISPER_*`, `YTDLP_*`, `RESOLVE_*`, `COMFY_*`, `YOUTUBE_*` (publish only)
- **Google Photos:** Picker or local mirror only — no full-library API sync

---

## Provisioning (Coding)

1. `configure-openclaw.py` — includes `media` agent + exec tools  
2. `seed-persona-os.sh` — seeds `workspace-media`  
3. `wire-paperclip-clawsum.py` — Paperclip assignee **Clawsum Media**  
4. Sync cockpit `authority.json` (ships with repo)  
5. Install FFmpeg, yt-dlp, Faster Whisper, auto-editor on Boss GPU host; set env prefixes in vault  
6. Agent Paperclip callbacks use `http://host.docker.internal:3102/api` (Host-rewriting proxy → loopback `:3100`). Never `https://paperclip.clawsum.com/api` from inside OpenClaw (Authelia 302). See `fix-paperclip-agent-proxy.sh`.

---

## Content factory (daily evergreen)

Boss ideas go to Hermes → Research → Content pack → Media render → Social queue.  
See [CONTENT-FACTORY.md](./CONTENT-FACTORY.md). Publish/schedule remains Tier 2.

## Hermes routing rule

When Boss asks for video/audio production, clips, thumbnails, or channel SEO packs:

1. Ack → Paperclip plan with assignee **Clawsum Media**  
2. Do **not** assign Hermes unless `Boss authorized Hermes: yes`  
3. Publish steps must include `ops.approvals`

## Related ops fixes

- Avenou GHL archive closeout / disposition: agents must register **work-products** + PATCH `done` via local agent API (`:3102`), not the public hostname.