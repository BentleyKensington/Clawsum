# Hermes usage policy (Boss authorization required)

**Default path for Gerald (2026-07-23):** browser **Hermes UI** (`hermes.${DOMAIN}` / `:9119`) is the **primary CEO chat face**.  
**Default path for work execution:** all governed tasks still go through **Paperclip** → **OpenClaw agents**.  
**Clawsum Hermes assignee** remains **opt-in only** for long autonomous runs that Boss explicitly assigns.

**Boss UI** = **Paperclip** (company Clawsum). It is not Hermes-branded.  
**Hermes UI** = Nous Hermes Agent dashboard (chat / exploration).  
**Clawsum Hermes** (Paperclip) = a **headless assignee** via OpenClaw session `paperclip:hermes`.

See [CEO-COCKPIT.md](./CEO-COCKPIT.md) for how these surfaces fit together.

---

## Two Hermes concepts

| Concept | Role | Access |
|---------|------|--------|
| **Hermes UI** (Nous dashboard) | CEO conversation entry (“JARVIS talks”) | `https://hermes…` behind ops portal |
| **Clawsum Hermes** (Paperclip assignee) | Long 50+ step jobs | Boss UI assignee + `Boss authorized Hermes: yes` |

Hermes UI must **not** hold unrestricted business credentials. Serious work → Paperclip task → cell-scoped OpenClaw agent.

---

## Architecture (production)

```text
Gerald
  → Hermes UI (browser) / Telegram / later Discord
      → ask / summarize / route intent
  → Paperclip Boss UI
      → tasks, approvals, budgets, audit
      → heartbeats → OpenClaw agents (Codex)
      → optional assignee Clawsum Hermes → session paperclip:hermes
```

---

## Hermes Agent web dashboard — enable as CEO face

| Item | Clawsum status |
|------|----------------|
| `hermes` CLI in Paperclip container | Install via `install-hermes-dashboard.sh` |
| `hermes dashboard` on :9119 | `hermes-dashboard.sh start` |
| Traefik route `hermes.${DOMAIN}` | `setup-ops-portal-traefik.sh` |
| Default production assignee path | Still `openclaw_gateway` (not `hermes_local`) |

```bash
bash /docker/clawsum/scripts/install-hermes-dashboard.sh
bash /docker/clawsum/scripts/hermes-dashboard.sh start
HERMES_HOST=hermes.yourdomain.com bash /docker/clawsum/scripts/setup-ops-portal-traefik.sh
```

Never expose `:9119` on `0.0.0.0` without Traefik auth.

**Clawsum cockpit skin:** theme + plugin overlay — see [../examples/hermes-cockpit/README.md](../examples/hermes-cockpit/README.md) and `bash scripts/install-hermes-cockpit.sh`.

---

## Why assignee Hermes stays gated

| Assignee | Runtime | LLM billing |
|----------|---------|-------------|
| **Clawsum Admin** (and specialists) | `openclaw_gateway` → Codex OAuth | ChatGPT Plus first |
| **Clawsum Hermes** (when Boss assigns) | `openclaw_gateway` → `paperclip:hermes` | Same Codex path |
| ~~`hermes_local`~~ | Deprecated | API-only |

---

## Boss rules (locked)

1. **Daily chat:** prefer Hermes UI; route actions into Paperclip.
2. **Do not** assign routine tasks to **Clawsum Hermes** unless the issue says **Boss authorized Hermes**.
3. **Admin** breaks down lists and delegates to specialists.
4. Use Hermes assignee only for **50+ step** autonomous work.
5. Add `Boss authorized Hermes: yes` when intentional.
6. Resume agents only per [RESUME-POLICY.md](./RESUME-POLICY.md).

---

## OpenClaw vs Hermes decision

```text
Gerald asks in Hermes UI
    ├─ answer-only / archive query → stay in Hermes (tier 0)
    ├─ needs task / approval → Paperclip issue (+ ops.approvals if tier 2)
    └─ long autonomous run → assignee Clawsum Hermes (explicit)

Boss creates task in Boss UI
    ├─ assign specialist → openclaw_gateway (preferred)
    └─ assign Clawsum Hermes → only if authorized
```

---

## Related

- [CEO-COCKPIT.md](./CEO-COCKPIT.md)
- [PAPERCLIP-OVERWATCH.md](./PAPERCLIP-OVERWATCH.md)
- [HERMES-OPENCLAW-ROUTING.md](./HERMES-OPENCLAW-ROUTING.md)
- [BOSS-OPS-PORTAL.md](./BOSS-OPS-PORTAL.md)
