# Memory Pipeline (Phase 1–2 — VPS)

**Status:** Phase 1 + Phase 2 dreaming live  
**Full local twin:** [LOCAL-STACK-PLAN.md](LOCAL-STACK-PLAN.md)  
**Policy:** [MEMORY_POLICY.md](../personas/clawsum/MEMORY_POLICY.md)

---

## Pipeline

```text
Text / ChatGPT archive
        │
        ▼
 Fact extraction (immediate)
        │
        ▼
 ops.memory_facts + Arcade graph
        │
        ▼
 Hourly dream — expire / dedupe / contradict / confidence bump
        │
        ▼
 Nightly dream — LLM compress hot subjects + Obsidian Admin/Memory/
        │
        ▼
 Weekly dream — deeper compress + Admin/Self-Model.md
```

---

## Schema

| Table | Role |
|-------|------|
| `ops.memory_facts` | Typed triples; `status=active\|historical` |
| `ops.memory_episodes` | Experiences |
| `ops.memory_dream_runs` | Consolidation job log |

---

## Commands (VPS)

```bash
# Immediate extract
python3 /docker/clawsum/scripts/memory-fact-extract.py --text "..."

# Archive → memory (Boss-approved)
python3 /docker/clawsum/scripts/promote-archive-to-memory.py --resume

# Dreaming
bash /docker/clawsum/scripts/run-memory-dream.sh hourly
bash /docker/clawsum/scripts/run-memory-dream.sh nightly
bash /docker/clawsum/scripts/run-memory-dream.sh weekly

# Install crons (America/Chicago)
bash /docker/clawsum/scripts/install-memory-dream-cron.sh
# or full Phase 2 deploy + smoke:
bash /docker/clawsum/scripts/deploy-memory-phase2.sh
```

### Cron schedule

| Stage | When (Chicago) | Job |
|-------|----------------|-----|
| Hourly | `:20` every hour | Dedupe / contradict / expire temporary |
| Nightly | `02:15` | + LLM compress (hot subjects) + `Admin/Memory/YYYY-MM-DD-dream.md` |
| Weekly | Sunday `03:30` | Deeper compress + `Admin/Self-Model.md` |

### Env

| Variable | Default |
|----------|---------|
| `MEMORY_EXTRACT_MODEL` | `gpt-4.1-mini` / OpenRouter flash |
| `MEMORY_DREAM_MODEL` | same as extract if unset |
| `CLAWSUM_SOURCE_HOST` | `vps` |

---

## Arcade

| Type | Role |
|------|------|
| `Fact` / `MemoryEntity` / `Episode` | Graph mirror |
| `Asserts` / `About` | Fact → entities |
| `Supersedes` | Winner → historized fact (dreaming) |

---

## Obsidian

| Path | Content |
|------|---------|
| `obsidian/Admin/Memory/*-dream.md` | Nightly/weekly dream notes |
| `obsidian/Admin/Latest-Dream.md` | Pointer to latest |
| `obsidian/Admin/Self-Model.md` | Weekly self-model touch-ups |
| `obsidian/Admin/Archive/*-archive-pulse.md` | ChatGPT archive poll (non-personal) |
| `obsidian/Admin/Memory/from-chatgpt-archive.md` | Rolling archive digest |

---

## Next

- Phase 3–4: local Ollama + Syncthing + `memory-sync.py` ([LOCAL-STACK-PLAN.md](LOCAL-STACK-PLAN.md))
