# Clawsum CEO Cockpit — access model & shell

**Preference (2026-07-23):** Browser **Hermes UI** (self-hosted Nous dashboard) is the **primary** CEO chat / interaction surface. Paperclip Boss UI, OpenClaw Control UI, and Grafana remain first-class ops surfaces behind the same ops portal.

---

## What “cockpit shell” means

Not a greenfield rewrite of Paperclip/OpenClaw. A **thin command home** that:

1. **Authenticates once** (Traefik ops-portal wall → later Authelia/SSO)
2. **Lands you on Hermes chat** as the default face (“JARVIS talks”)
3. **Deep-links** into the real systems of record for everything else
4. **Gradually adds** CEO-only pages (approvals queue, business cells, archive search) that call Paperclip + Postgres — without bypassing governance

```text
┌─────────────────────────────────────────────────────────────┐
│  Clawsum CEO Cockpit (shell)                                 │
│  Auth: Traefik basic auth → later Authelia                   │
│                                                              │
│  Default tab: Hermes / JARVIS chat  ← PRIMARY                │
│  Tabs / tiles:                                               │
│    · Approvals (Paperclip + overwatch schema)                │
│    · Business cells (status cards)                           │
│    · Tasks → opens Boss UI (or embed later)                  │
│    · Gateway → OpenClaw Control UI                           │
│    · Health → Grafana                                        │
│    · Archive (ChatGPT RAG — Phase 6)                         │
└───────────────┬─────────────────────────────────────────────┘
                │ deep links / iframes / APIs
     ┌──────────┼──────────┬──────────┬──────────┐
     ▼          ▼          ▼          ▼          ▼
 Hermes UI   Boss UI   OpenClaw    Grafana    Postgres
 :9119       :3100     Control     :3000      overwatch
 (chat)    (tasks)     UI          (metrics)  + archive
```

### Phased shell (do this order)

| Phase | What you get | Build |
|-------|----------------|-------|
| **A — Portal + Hermes** | HTTPS wall; Hermes as bookmark #1 | `setup-ops-portal-traefik.sh` + `hermes-dashboard.sh start` |
| **A+ — Hermes cockpit** | Clawsum theme, logo, Brief/Approvals/Grafana tabs | `examples/hermes-cockpit` + `install-hermes-cockpit.sh` |
| **B — Optional home URL** | Single `cockpit.${DOMAIN}` redirect/iframe | Tiny static page (only if you want one hostname) |
| **C — Deeper overwatch** | Richer approvals / cells wired to Paperclip | Extend plugin + [PAPERCLIP-OVERWATCH.md](./PAPERCLIP-OVERWATCH.md) |
| **D — Custom chat** | Replace Hermes TUI chat | Optional — **do not start here** |

**Recommendation:** Ship **A + A+** now. Defer **B** and **D**.

### Hermes cockpit overlay (approved path)

```bash
bash scripts/install-hermes-dashboard.sh
bash scripts/hermes-dashboard.sh start
bash scripts/install-hermes-cockpit.sh
bash scripts/hermes-dashboard.sh stop && bash scripts/hermes-dashboard.sh start
```

Details: [../examples/hermes-cockpit/README.md](../examples/hermes-cockpit/README.md)

Replace placeholder SVGs in `deploy/examples/hermes-cockpit/assets/` with your logo/crest anytime, then re-run install.

---

## Surface map (what each UI is for)

| Surface | Hostname (example) | You use it for | Not for |
|---------|-------------------|----------------|---------|
| **Hermes UI** | `hermes.${DOMAIN}` | CEO conversation, exploration, “ask JARVIS”, long-session feel | Formal approvals, budgets, agent registry |
| **Boss UI (Paperclip)** | `boss.${DOMAIN}` | Tasks, assignees, CLA-41, heartbeats, spend, activity | Infra charts, gateway pairing |
| **OpenClaw Control UI** | `clawsum.${DOMAIN}` | Channels, Telegram, Gmail/gog, devices, Codex login | Business task board |
| **Grafana** | `grafana.${DOMAIN}` | CPU/RAM/disk, probes, container health | Gmail bodies, CRM, chat |
| **Telegram** | mobile | Alerts, daily brief, quick approvals later | Full dashboard |
| **Discord** | later | Same as Telegram + channel layout | Source of truth |

### Control model (unchanged)

```text
Hermes / JARVIS talks.     ← primary browser face
Paperclip manages.         ← Boss UI + overwatch schema
OpenClaw acts.             ← Control UI configures tools; agents execute
Gerald approves.           ← Approvals in Boss UI / cockpit / Discord later
```

**Hermes primacy** means *conversation entry point*, not *credential owner*. High-risk actions still create Paperclip tasks / approval objects.

---

## Ops portal — enable Hermes as main access

On the VPS:

```bash
cd /docker/clawsum

# 1) Install Nous Hermes web extras (once)
bash scripts/install-hermes-dashboard.sh

# 2) Start dashboard on loopback :9119
bash scripts/hermes-dashboard.sh start
bash scripts/hermes-dashboard.sh status

# 3) Traefik routes (Boss + OpenClaw + Grafana + Hermes)
HERMES_HOST=hermes.yourdomain.com \
BOSS_HOST=boss.yourdomain.com \
OPENCLAW_HOST=clawsum.yourdomain.com \
GRAFANA_HOST=grafana.yourdomain.com \
bash scripts/setup-ops-portal-traefik.sh

# 4) OpenClaw behind same wall (optional but recommended)
python3 scripts/patch-control-ui-trusted-proxy.py
docker compose restart openclaw-gateway
```

DNS A records: `hermes`, `boss`, `clawsum`, `grafana` → VPS IP.

**SSH fallback** (no DNS yet):

```bash
ssh -L 9119:127.0.0.1:9119 -L 3100:127.0.0.1:3100 -L 3000:127.0.0.1:3000 clawsum
# http://localhost:9119  Hermes
# http://localhost:3100  Boss UI
# http://localhost:3000  Grafana
# Control UI: https://clawsum.… or tunnel gateway UI port if used
```

---

## Two “Hermes” concepts (do not conflate)

| Name | What it is | When |
|------|------------|------|
| **Hermes UI** (Nous dashboard :9119) | Browser chat / config surface — **CEO face** | Daily interaction |
| **Clawsum Hermes** (Paperclip assignee) | Headless long-run via `openclaw_gateway` → `paperclip:hermes` | Only when Boss authorizes 50+ step jobs |

Policy: [HERMES-POLICY.md](./HERMES-POLICY.md) · Routing: [HERMES-OPENCLAW-ROUTING.md](./HERMES-OPENCLAW-ROUTING.md)

---

## Recommendations

1. **Make Hermes the home tab** in browser; pin Boss UI for CLA-41 / approvals.
2. **Do not** give Hermes UI raw PITs / banking / production deploy tools.
3. **Keep** one-bot-per-channel on Telegram/Discord when you expand channels.
4. **Build cockpit Phase C** on top of [PAPERCLIP-OVERWATCH.md](./PAPERCLIP-OVERWATCH.md), not by scraping UIs.
5. **VPN-first** still preferred; Traefik basic auth is the minimum wall until Authelia.

Related: [BOSS-OPS-PORTAL.md](./BOSS-OPS-PORTAL.md) · [BOSS-ACCESS-GUIDE.md](./BOSS-ACCESS-GUIDE.md) · [RESUME-POLICY.md](./RESUME-POLICY.md)
