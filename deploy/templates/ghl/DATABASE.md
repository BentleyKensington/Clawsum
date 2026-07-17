# DATABASE.md — {AGENT_ID}

**Database:** `ghl` (this account's schema only)
**Host:** `postgres:5432` (Docker network `clawsum`)
**User:** `{DB_USER}` (isolated role — not shared `clawsum` user)
**Primary schema:** `{SCHEMA_PREFIX}`

```
postgresql://{DB_USER}:***@postgres:5432/ghl
```

Set password via env `{ENV_DB_PASSWORD}` on the VPS (never commit `.env`).

## Crossover

- **Never** query another GHL account schema unless this agent owns that schema.
- **Cross-domain:** Paperclip tasks only — no cross-DB queries between agents.
