# MEMORY_POLICY.md — Clawsum

| Store | Allowed | Forbidden |
|-------|---------|-----------|
| Agent `memory/YYYY-MM-DD.md` | Session notes, next steps | Secrets, full mail bodies, PITs |
| `MEMORY.md` (Hermes) | Ranked pending queue | Raw credentials |
| Postgres `ops.*` | Emails, approvals, CRM, archive metadata | Treat as system of record |
| Postgres `ops.memory_facts` / `ops.memory_episodes` | Structured durable facts + episodes (Phase 1 memory graph) | Secrets, API keys, passwords, unverified personal dump into business scope |
| ArcadeDB `Fact` / `MemoryEntity` / `Episode` | Graph mirror of memory facts (relationships) | Sole SoR — Postgres wins on conflict |
| Obsidian | Gerald-confirmed durable narrative | Unreviewed personal dump |
| Chat | Summaries and questions | Secret material |
| Redis working memory | Hot session buffer (TTL) | Durable truth; do not Syncthing |

Personal-scope archive never promotes to business agents without Gerald re-scope.

**Pipeline:** [MEMORY-PIPELINE.md](../../docs/MEMORY-PIPELINE.md) · **Local twin:** [LOCAL-STACK-PLAN.md](../../docs/LOCAL-STACK-PLAN.md)
