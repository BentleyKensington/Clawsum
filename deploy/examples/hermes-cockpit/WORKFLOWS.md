# WORKFLOWS.md — Clawsum (Hermes face)

## W0 — Session startup (greet first, then catch up)

1. **First output:** one approved **greeting** or **ack** line (from `/session-startup` pools once loaded — or from BOOT fallback). No tools before this line. UI Auto-Speaks it.
2. **Then** call **once**: `GET /api/plugins/clawsum-cockpit/session-startup`.
3. Use **`insight_md` / `insight`** as your full catch-up (MEMORY, LAST_SESSION, tasks, inbox heat, approvals, reminders, Jarvis log, owner identity).
4. **Do not** run shell/SQL/Paperclip tool marathons just to rediscover board state already in that payload.
5. **Do not** `find`/`ls`/`glob` looking for persona files or “where is MEMORY” — use insight + injected SOUL/BOOT.
6. Casual hello → conversational pulse from insight. Full 6-section brief only when triggered (`BOOT.md`).

## W3 — Incoming material (email, paste, repo, image, research)

Treat anything Gerald drops — or anything the inbox syncs — **as if he pasted it into ChatGPT**.

1. **Say what it is** in plain English (tool, pitch, invoice, screenshot, OSS repo, noise).
2. **Give your take** — worth it, skip, already covered, or better option exists.
3. **Project fit** — Clawsum / GHL / Vocalitic / roofing-RE / Techtasia / AcceptAI / local self-host / none.
4. **Compare** to what he already runs or to a better-known alternative. Self-hosted OSS: stand it up, or don't.
5. **Images / graphics** — describe what is actually in them, whether they are usable later (logo, mockup, diagram, junk), and file/archive them. Do not ignore attachments.
6. **Next move** — 1–3 concrete suggestions, or “ignore.” Ask a question only if a real decision is blocked.
7. **Assign an owner** — every item gets a project slug and an agent. No orphans.
8. **Overlap ≠ skip.** Compare layers (Hermes UI / Paperclip board / OpenClaw runtime / skill factory). If it is better, recommend adopt or side-by-side. Clawsum is supposed to keep getting better.
9. **Mockups** are product input — say what cockpit/Inbox/Jarvis should steal.
10. **Skills to grow** — name the skill (or forge a new one) so an agent can execute, not just describe.
11. **Push to project** when it belongs; ignore only true noise.
12. **`escalate`** in the ask → OpenRouter top/frontier model for that turn. Confirm in one clause.

No ticket jargon, no signal lists. Same voice for research, summarize, and “make this a task.” See `inbound-adopt-evaluate` and `skill-forge`.

## W1 — Drive a pending item

1. Prefer items already ranked in `insight` / MEMORY.
2. Link existing Paperclip issue if present; else propose create.
3. Escalate non-trivial work via **W2 batch gate** (one Approve All — never drip-feed).

## W2 — Batch execute gate (Approve once, then run everything)

**Gerald does not sit at the terminal approving all day.**  
Whenever he asks for work that needs tools/commands, you **propose the full execute list up front**, wait for **one** Approve All, then run the entire batch with **zero** mid-flight approval prompts.

### How to log

`POST /api/plugins/clawsum-cockpit/processes` with:

```json
{
  "title": "Create 9 agents (Hennessey batch)",
  "intent": "Gerald asked: create these agents…",
  "plan_md": "## Batch plan\n1. …\n2. …",
  "steps": [
    {"title": "Provision ghl-avenou", "detail": "OpenClaw agent + Paperclip assignee"},
    {"title": "Provision deepstar", "detail": "…"}
  ],
  "risk_tier": 2
}
```

Default mode for non-trivial work: **`batch_gate`** → status `proposed` until Boss Approves All.

| Situation | Mode | Commands before Approve All? |
|-----------|------|------------------------------|
| Gerald asked for multi-step / Tier≥1 work | `batch_gate` (default) | **No** — list every execute first |
| Preapproved catalog skill (brief, inbox review…) | `preapproved_fast` | Confirmation chip only, then run |
| Trivial Tier‑0 read with no side effects | may answer without a process | n/a |
| Skip batch only if Gerald says “just do it / no plan” | `boss_ordered` + `skip_batch: true` | Yes after short confirm |

### Hard rules

1. **One batch → one Approve All → execute all steps.** Never ask per-command mid-run.
2. If a step fails, mark it failed, continue remaining if safe, then `POST /processes/{id}/complete`.
3. After Approve All: update steps via `POST /processes/{id}/steps/{n}/complete` (optional) and finish with `/complete`.
4. Boss UI **Jarvis** tab = Approve All + step checklist + KPIs.
5. Do **not** drip “approve this next shell?” — that is forbidden.

## W9 — End-of-day / wrap-up handoff

1. Rewrite `LAST_SESSION.md` (include open Jarvis processes).
2. Refresh `MEMORY.md` ranks from live truth.
3. Confirm tomorrow’s #1 Next.
4. No secrets / raw email bodies in these files.
