# Clawsum Local Stack Plan

**Status:** Phase 1–2 complete on VPS (memory graph + dreaming). Phases 3–5 remain.  
**Audience:** Boss + coding/admin agents  
**Related:** [DATA-ARCADEDB-VS-POSTGRES.md](DATA-ARCADEDB-VS-POSTGRES.md), [MEMORY_POLICY.md](../personas/clawsum/MEMORY_POLICY.md), [LLM-ROUTING.md](LLM-ROUTING.md), [OPENROUTER-AND-VOICE.md](OPENROUTER-AND-VOICE.md), [BOSS-OBSIDIAN-WINDOWS.md](BOSS-OBSIDIAN-WINDOWS.md), [MEMORY-PIPELINE.md](MEMORY-PIPELINE.md)

---

## 1. Goal

Run a **complete Clawsum twin on the Boss PC** (local LLM, STT, TTS, DBs, Hermes/Paperclip/OpenClaw where practical) that **syncs** with the VPS production stack — without two brains freely double-writing operational state.

Local is for:

- Offline / low-latency chat and voice
- Private fact extraction and dreaming when the VPS is unreachable
- GPU-bound models (4070-class or better)
- Boss-side Obsidian editing with bidirectional vault sync

VPS remains:

- Public ingress (boss.clawsum.com, Telegram, Gmail cron)
- System of record for business ops (Gmail, approvals, CRM pipelines)
- Primary nightly dream host (unless Boss opts local-primary later)

---

## 2. Architecture overview

```text
┌──────────────────────────── Local PC ────────────────────────────┐
│  Boss UI / Obsidian / Mic+Speakers                               │
│       │                                                          │
│  Cockpit (Hermes plugin) ──► local /tts + /transcribe            │
│       │                      (Piper/Kokoro + faster-whisper)     │
│  Hermes + Paperclip + OpenClaw (optional profile)                │
│       │                                                          │
│  Fact extractor (Ollama) ──► Postgres memory_* ──► Arcade graph   │
│       │                                                          │
│  Redis (working memory) · MinIO (blobs) · Ollama (chat+embed)    │
│       │                                                          │
│  Sync workers ◄──────────────────────────────────────────────┐   │
└──────────────────────────────────────────────────────────────┼───┘
                                                               │
                         Syncthing (Obsidian)                  │
                         Memory upsert API (facts/graph)       │
                         Ops pull (read-mostly Postgres)       │
                                                               │
┌──────────────────────────── VPS ─────────────────────────────┼───┐
│  Traefik · Authelia · boss.clawsum.com                       │   │
│  Postgres (ops SoR) · ArcadeDB · Obsidian vault              │   │
│  Paperclip · Hermes · OpenClaw · Gmail crons · Grafana       │   │
│  Phase 1 memory pipeline (cloud LLM extract OK)              │   │
│  Nightly dreaming (primary)                                  │   │
└──────────────────────────────────────────────────────────────┴───┘
```

### Memory pipeline (both hosts)

```text
Conversation / email / note
        │
        ▼
 Fact Extraction          ← Immediate (seconds)
        │
        ▼
 Working Memory (Redis)   ← TTL session buffer
        │
        ▼
 Postgres ops.memory_*    ← SoR for facts/episodes
        │
        ▼
 ArcadeDB graph           ← typed entities + relationships
        │
        ▼
 Dreaming / consolidation ← Hourly / nightly / weekly / monthly
        │
        ▼
 Long-term semantic + Obsidian narrative
        │
        ▼
 Personality · Planning · Retrieval
```

---

## 3. Layer map (design → implementation)

| Layer | What it stores | Local component | VPS component | Sync |
|-------|----------------|-----------------|---------------|------|
| L1 Working memory | Hot session facts | Redis `local` | Redis `orchestration` | **No** (ephemeral) |
| L2 Fact extraction | Structured triples | Ollama small model | OpenAI/OpenRouter (Phase 1) | Facts sync |
| L3 Knowledge graph | Entities + edges | ArcadeDB | ArcadeDB | Bidirectional upsert |
| L4 OKF-style typing | Entity / Rel / Attr / Observation | Same Arcade types | Same | Via graph sync |
| L5 Dreaming | Compaction / historize | Optional local hourly | **Primary nightly** | Dream runs logged in Postgres |
| L6 Compression | GC duplicates | Dream worker | Dream worker | Idempotent merges by `fact_key` |
| L7 Semantic abstraction | Preferences, interests | Weekly dream | Weekly dream | Promote to Obsidian |
| L8 Episodic | Experiences | `ops.memory_episodes` + vault | Same | Sync rows + Syncthing notes |
| L9 Procedural | Workflows | Graph `Procedure` (later) | Same | Later phase |
| L10 Importance | Critical→Temporary | Column on facts | Same | Sync |
| L11 Confidence | user_stated→guessed | Column on facts | Same | Sync |
| L12 Retrieval | Layered recall | Local Hermes tools | VPS Hermes tools | Shared Postgres/Arcade read |
| L13 Reflection | “What did we learn?” | Weekly job | Weekly job | Obsidian `Admin/Self-Model.md` |

---

## 4. Local hardware & model targets

### Assumed Boss hardware

| Resource | Target |
|----------|--------|
| GPU | NVIDIA 8GB+ VRAM (RTX 4070 Super class OK) |
| RAM | 32GB+ recommended |
| Disk | 100GB+ free for models + Docker volumes |
| OS | Windows 10/11 + Docker Desktop (WSL2 backend) |

### Model roles

| Role | Local default | Fallback |
|------|---------------|----------|
| Chat / Hermes | Qwen2.5-14B or Llama-3.1-8B (quality/VRAM tradeoff) | VPS OpenRouter / Codex |
| Fact extraction | Gemma-2-9B / Qwen2.5-7B Instruct (JSON mode) | `gpt-4.1-mini` / flash via OpenRouter |
| Embeddings | `bge-m3` or `nomic-embed-text` via Ollama | OpenAI embeddings |
| STT | faster-whisper `large-v3` or `distil-large-v3` | OpenAI Whisper API |
| TTS | Piper (`en_US-lessac-medium`) or Kokoro | ElevenLabs / OpenAI TTS |

### VRAM budget (guideline)

| Load | Approx VRAM |
|------|-------------|
| 7B–9B Q4_K_M chat | 5–7 GB |
| Whisper large-v3 | 3–5 GB (can CPU-offload) |
| Embeddings | &lt;1 GB |
| **Rule** | Don’t run chat + whisper-large simultaneously on 8GB; queue STT or use `distil` / `small` while chatting |

---

## 5. Docker Compose — local profile

### New file (to create in Local Phase)

`deploy/docker-compose.local.yml` (extends / overrides main compose):

| Service | Image / build | Ports (localhost) | Notes |
|---------|---------------|-------------------|-------|
| `postgres` | same as VPS | `5433:5432` | Avoid clash with any local PG |
| `arcadedb` | same | `2480`, `5434` | Separate volume `clawsum_local_arcade` |
| `redis` | same | `6379` | Working memory only |
| `minio` | same | `9000`/`9001` | Optional local blobs |
| `ollama` | `ollama/ollama` | `11434` | GPU passthrough |
| `whisper` | `fedirz/faster-whisper-server` or custom | `8090` | OpenAI-compatible `/v1/audio/transcriptions` |
| `tts` | Piper HTTP wrapper or Kokoro | `8091` | Expose `/v1/audio/speech` shape |
| `paperclip` | same (optional) | `3100` | Profile `local-orch` |
| `openclaw-gateway` | same (optional) | `18789` | Profile `local-agents` |

**Not required on day one of local:** Traefik, Authelia, Prometheus full stack, Gmail cron (pull from VPS instead).

### Env file

`deploy/.env.local.example` → copy to `.env.local`:

```bash
CLAWSUM_ROLE=local
CLAWSUM_SOURCE_HOST=local
POSTGRES_PORT=5433
ARCADEDB_URL=http://127.0.0.1:2480
OLLAMA_HOST=http://127.0.0.1:11434
SPEECH_STT_PROVIDER=local
SPEECH_STT_URL=http://127.0.0.1:8090/v1/audio/transcriptions
SPEECH_TTS_PROVIDER=local
SPEECH_TTS_URL=http://127.0.0.1:8091/v1/audio/speech
MEMORY_EXTRACT_PROVIDER=ollama
MEMORY_EXTRACT_MODEL=qwen2.5:7b-instruct
MEMORY_SYNC_URL=https://boss.clawsum.com/api/...   # or SSH tunnel
MEMORY_SYNC_TOKEN=
```

Cockpit `plugin_api.py` already abstracts TTS/STT behind env — local URLs plug in without UI rewrite.

---

## 6. Sync topology (both systems)

### Hard rules

1. **One primary writer per domain.**
2. **Never sync Redis working memory.**
3. **Never sync secrets** (`.env`, OAuth tokens, Authelia DB) via Syncthing.
4. **Dreaming has one primary host** (default: VPS nightly). Local may run Immediate + Hourly only unless `CLAWSUM_DREAM_PRIMARY=local`.
5. Facts merge by **`fact_key`** + **`updated_at`** + **confidence rank** (confirmed &gt; user_stated &gt; observed &gt; inferred &gt; guessed).

### Channels

| Channel | Tool | Direction | Interval | Payload |
|---------|------|-----------|----------|---------|
| Obsidian vault | **Syncthing** | Bidirectional | Continuous | `/docker/clawsum/obsidian` ↔ `~/ClawsumVault` |
| Memory facts/episodes | `memory-sync.py` over HTTPS or SSH | Bidirectional upsert | 5–15 min | JSON rows + tombstones |
| Arcade graph | Same worker mirrors after PG upsert | Bidirectional | With facts | Vertices/edges by `clawsum_id` |
| Ops business tables | `pg_dump`/`psql` or read replica | **VPS → local** (read-mostly) | Hourly / on demand | emails, tasks, CRM (no secrets) |
| Session briefs | Optional | VPS → local | 15 min | `ops.session_briefs` |
| Models / Docker images | Manual / pull | Local only | — | Not synced |

### Conflict policy

| Case | Resolution |
|------|------------|
| Same `fact_key`, different object | Higher confidence wins; loser → `status=historical` + `Supersedes` edge |
| Same confidence, different hosts | Newer `updated_at` wins |
| `importance=temporary` | Expire via `valid_to`; do not resurrect from older peer |
| Episode edit on both sides | Merge summaries if non-overlapping; else keep both with distinct IDs |
| Obsidian file conflict | Syncthing `.sync-conflict-*`; Boss resolves in vault |

### Network options

| Mode | How |
|------|-----|
| A. Always-on | Tailscale / WireGuard between PC and VPS; sync over private IP |
| B. Intermittent | Queue local facts to `ops.memory_outbox`; flush when online |
| C. Air-gapped session | Extract + dream locally; USB/Syncthing relay later |

Replace SSHFS-as-SoR ([BOSS-OBSIDIAN-WINDOWS.md](BOSS-OBSIDIAN-WINDOWS.md)) with Syncthing for the local twin; SSHFS can remain a thin “peek at VPS only” mount if desired.

---

## 7. Speech local wiring

### STT

1. Run faster-whisper server with OpenAI-compatible transcription endpoint.
2. Set cockpit / `speech_api.py`:
   - `SPEECH_STT_PROVIDER=local`
   - `SPEECH_STT_URL=http://127.0.0.1:8090/v1/audio/transcriptions`
3. Keep Chrome Web Speech as optional UI path; Whisper local as listen backup (same as today’s Whisper backup pattern).

### TTS

1. Piper or Kokoro HTTP service returning `audio/mpeg` or `audio/wav`.
2. Adapt `/tts` in `plugin_api.py` to POST text to local URL when `SPEECH_TTS_PROVIDER=local`.
3. Keep greeting MP3 cache; regenerate cache locally once with chosen voice.
4. Cloud fallback: if local fails → ElevenLabs/OpenAI (existing path).

### Auto-Send / Auto-Speak

UI toggles already exist on VPS cockpit; they work unchanged against local speech backends.

---

## 8. LLM local wiring

| Consumer | Local | Fallback |
|----------|-------|----------|
| Hermes default chat | Ollama OpenAI-compatible `/v1` | OpenRouter |
| Fact extractor | Ollama JSON | OpenAI mini |
| Gmail deep review | Prefer VPS (needs live mail) | — |
| Embeddings for Arcade | Ollama embed | Skip until vectors phase |

OpenClaw / Hermes model config points at `http://host.docker.internal:11434/v1` on Docker Desktop.

---

## 9. Multi-stage consolidation schedule

| Stage | Cadence | Where | Actions |
|-------|---------|-------|---------|
| Immediate | On each interaction | Local **and** VPS | Extract facts → Redis → Postgres → Arcade |
| Short-term | Hourly | Local if awake; else VPS | Dedupe, contradict, confidence bumps |
| Nightly dream | 02:00 local VPS TZ | **VPS primary** | Compress, historize GPUs/prefs, archive obsolete |
| Weekly | Sunday | VPS | Semantic preferences, procedures, Obsidian promo |
| Monthly | 1st | VPS | Prune Temporary, re-score importance, `Admin/Self-Model.md` |

Phase 1 (VPS) delivers Immediate extract + schema only. Dreaming workers are Phase 2+.

---

## 10. Phased delivery

### Phase 1 — VPS memory foundation (**done**)

- [x] Design Local Stack Plan (this doc)
- [x] `ops.memory_facts` / `ops.memory_episodes` / `ops.memory_dream_runs`
- [x] Arcade `Fact` / `Episode` / `MemoryEntity` + edges
- [x] `memory-fact-extract.py` (cloud LLM)
- [x] MEMORY policy update + deploy to VPS
- [x] Smoke: extract sample text → PG → Arcade (run `deploy-memory-phase1.sh`)
- [x] ChatGPT archive import + classify (2,238 conversations)
- [x] Promote archive → memory graph (`promote-archive-to-memory.py`, business/mixed only)

### Phase 2 — VPS dreaming (hourly + nightly) (**done**)

- [x] Deduper / contradictor (`memory-dream.py --stage hourly`)
- [x] Nightly consolidation agent + LLM compress for hot subjects
- [x] Obsidian daily dream note under `Admin/Memory/`
- [x] Weekly dream + `Admin/Self-Model.md`
- [x] Crons via `install-memory-dream-cron.sh` (Chicago TZ)

### Phase 3 — Local inference stack

- `docker-compose.local.yml` + Ollama + whisper + TTS
- Point speech + extract at local
- Offline outbox

### Phase 4 — Sync

- Syncthing Obsidian
- `memory-sync.py` bidirectional
- Tailscale recommended
- Ops read-mostly pull

### Phase 5 — Full local orchestration (optional)

- Local Paperclip/Hermes/OpenClaw profiles
- Local Boss UI against local Hermes
- Split-brain safeguards (role locks)

---

## 11. Security & policy

| Rule | Detail |
|------|--------|
| Secrets | Never in facts, Obsidian, or Syncthing share |
| Personal vs business | Personal facts `scope=personal` — no auto-promote to business agents ([AUTHORITY.md](../skills/AUTHORITY.md)) |
| Approval | Durable Obsidian promotion still Boss-gated where policy says |
| Local exposure | Bind Ollama/whisper/TTS to `127.0.0.1` only |
| Sync auth | Token + mTLS or SSH; no open internet memory API without Authelia |

---

## 12. Acceptance criteria

### Phase 1 (VPS)

1. Tables exist; extractor inserts ≥1 fact from sample text.
2. Arcade shows matching `Fact` vertex and `About`/`Asserts` edges.
3. `MEMORY_POLICY.md` documents the new stores.
4. No secrets in extracted sample output.

### Local stack ready

1. Local Ollama answers a Hermes/OpenAI-compatible chat call.
2. Local STT transcribes a 5s wav; local TTS returns playable audio.
3. Syncthing vault settles both sides within 1 minute of edit.
4. Fact created on local appears on VPS within sync interval (and reverse).
5. Killing WAN: local chat+voice+extract still works; outbox drains later.

---

## 13. Recommended Boss checklist (when starting local)

1. Install Docker Desktop + NVIDIA Container Toolkit (WSL2).
2. Install Obsidian + Syncthing; share vault folder (not `.env`).
3. Copy `.env.local.example` → `.env.local`; set `CLAWSUM_SOURCE_HOST=local`.
4. `docker compose -f docker-compose.yml -f docker-compose.local.yml --profile local up -d`
5. `ollama pull` extract + chat + embed models.
6. Wire cockpit speech URLs; hard-refresh Boss UI (or local UI).
7. Run `memory-fact-extract.py --text "..."` against local, then sync once.

---

## 14. Non-goals (explicit)

- Replacing VPS Postgres as ops SoR for Gmail/approvals
- Syncing full chat transcripts as memory blobs (facts only)
- Running two independent nightly dreams that both mutate the same active facts without a primary
- Putting Qdrant in Phase 1–3 (Arcade vectors first)
- Shipping Neo4j alongside Arcade

---

## 15. File index (expected)

| Path | Purpose |
|------|---------|
| `deploy/docs/LOCAL-STACK-PLAN.md` | This plan |
| `deploy/docs/MEMORY-PIPELINE.md` | VPS Phase 1+ memory pipeline ops |
| `deploy/postgres-init/19-ops-memory-graph.sql` | Schema |
| `deploy/scripts/memory-fact-extract.py` | Immediate extractor |
| `deploy/scripts/clawsum_arcade.py` | Graph mirror helpers |
| `deploy/scripts/deploy-memory-phase1.sh` | Apply + smoke on VPS |
| `deploy/scripts/memory-dream.py` | Phase 2 consolidation (hourly/nightly/weekly) |
| `deploy/scripts/run-memory-dream.sh` | Paperclip-venv runner + Obsidian sync |
| `deploy/scripts/install-memory-dream-cron.sh` | Dream crons |
| `deploy/scripts/deploy-memory-phase2.sh` | Deploy + smoke Phase 2 |
| `deploy/docker-compose.local.yml` | *(Phase 3)* Local services |
| `deploy/scripts/memory-sync.py` | *(Phase 4)* Bidirectional sync |

---

*Last updated: 2026-08-04 — authored with Phase 1 VPS-first execution.*
