# Hermes usage policy (Boss authorization required)

**Default:** all Boss UI tasks go to **OpenClaw agents** (Admin, Data, Coding, RE, GHL, …).  
**Hermes** is **opt-in only** for long autonomous runs that Boss explicitly assigns.

**Boss UI** = **Paperclip** (company Clawsum). It is not Hermes-branded.  
**Hermes** on Clawsum = a **headless Paperclip assignee** — not a standalone web product in our stack.

---

## Architecture (production)

```text
Boss UI (Paperclip / Clawsum branding)
    → you create task, assignee = Clawsum Hermes (only when authorized)
    → Paperclip heartbeat (OFF by default for Hermes)
    → adapter: openclaw_gateway
    → OpenClaw admin session: paperclip:hermes
    → Codex / ChatGPT Plus
    → results in Paperclip task + Obsidian (Paperclip/ or assignee folder)
```

There is **no** separate Hermes hostname, workspace, or Telegram agent in the default Clawsum design.

---

## Hermes Agent web dashboard (Nous product) — not deployed

Nous Hermes Agent ships a **browser dashboard** (`hermes dashboard`, default `http://127.0.0.1:9119`) for config, sessions, cron, and embedded chat. **Clawsum does not run this today:**

| Item | Clawsum status |
|------|----------------|
| `hermes` CLI in Paperclip container | Not installed |
| `hermes_local` adapter | Deprecated; not used on VPS |
| `hermes dashboard` on :9119 | Not started |
| Traefik route for Hermes UI | Not configured |

To add it later (optional): install `hermes-agent[web]`, bind to loopback, route via Traefik with ops-portal auth — see [MASTER-TASK-LIST.md](./MASTER-TASK-LIST.md) § Hermes UI.

**Until then:** manage Hermes only through **Boss UI** (assignee + activity feed).

---

## Why

| Assignee | Runtime | LLM billing |
|----------|---------|-------------|
| **Clawsum Admin** (and other OpenClaw agents) | `openclaw_gateway` → gateway Codex OAuth | **ChatGPT Plus** (subscription) first |
| **Clawsum Hermes** (when Boss assigns) | `openclaw_gateway` → **admin** session `paperclip:hermes` | **ChatGPT Plus / Codex** (same as Admin) |
| ~~`hermes_local`~~ | Deprecated on Clawsum — API-only, heartbeat **off** |

Hermes also bypasses Telegram visibility unless you mirror results in the task.

---

## Boss rules (locked)

1. **Do not** assign routine tasks, triage, or your task list to **Clawsum Hermes** unless the issue says **Boss authorized Hermes**.
2. **Admin** breaks down lists and delegates to specialists (Data, Coding, RE, GHL, …).
3. Use Hermes only when you need **50+ step** autonomous work (large refactor, multi-repo sweep) and accept API usage.
4. In issue description, add: `Boss authorized Hermes: yes` when intentional.
5. **Paperclip liaison** agent may *suggest* Hermes; Boss must change assignee to Hermes manually.

---

## Where this is enforced

| Layer | Enforcement |
|-------|-------------|
| **Boss UI** | You choose assignee — keep Hermes off default |
| **admin SOUL / ESCALATION** | Text policy on VPS (`seed-persona-os.sh`) |
| **paperclip / admin WORKFLOWS** | Do not auto-route to Hermes |

---

## OpenClaw vs Hermes decision

```text
Boss creates task
    ├─ assign Clawsum Admin / specialist → openclaw_gateway (preferred, Codex)
    └─ assign Clawsum Hermes ONLY if Boss authorized → openclaw_gateway session paperclip:hermes (same Codex path)
    └─ (optional future) standalone hermes_local → API billing — not deployed on Clawsum VPS
```

---

## Related

- [OPENAI-AUTH.md](./OPENAI-AUTH.md) — Codex first, API backup  
- [PAPERCLIP-SETUP.md](./PAPERCLIP-SETUP.md) — adapters, protocol fix  
- [BOSS-UI-AND-MONITORING.md](./BOSS-UI-AND-MONITORING.md) — task progress  
