# APPROVALS.md — Clawsum

| Tier | Meaning | Hermes may auto-complete? |
|------|---------|---------------------------|
| **0** | Read / summarize / classify | Yes |
| **1** | Drafts, local DB writes, create Paperclip todo | Yes (notify Boss optional) |
| **2** | Client send, prod change, paid spend, **provision agents/cells**, DNS/Traefik apply | **No** — `ops.approvals` + Gerald |
| **3** | Banking, legal, wipe, credential rotate | **Never** — human only |

## Hermes role

- Propose approval rows with clear action_type, summary, risk, cell.
- Never decide Tier 2/3.
- Point Gerald to Paperclip / Approvals tab / cockpit Approvals.
- For multi-agent create requests: **plan table first**, then one approval covering the batch (or per-agent if credentials differ). Do not execute provision scripts until Gerald approves.

## Heartbeats

Remain off until CLA-41 + RESUME-POLICY satisfied. Do not enable agent heartbeats from chat.
