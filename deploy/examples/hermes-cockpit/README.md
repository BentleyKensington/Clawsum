# Clawsum Hermes Cockpit overlay

Reskin + extend the self-hosted **Hermes web dashboard** into a Clawsum CEO cockpit — custom theme/logo, Approvals/Brief tabs, Grafana embed, without forking Hermes.

Upstream capability: [Extending the Dashboard](https://hermes-agent.nousresearch.com/docs/user-guide/features/extending-the-dashboard) (themes + UI plugins + FastAPI backend plugins). Pattern inspired by Nous `strike-freedom-cockpit`.

---

## Contents

```text
hermes-cockpit/
├── README.md                 (this file)
├── SOUL.md                   proactive Hermes instructions (archive + Paperclip)
├── theme/clawsum-command.yaml
├── assets/                   logo.svg, crest.svg, hero.svg, bg.svg (shipping Clawsum brand)
└── plugin/clawsum-cockpit/
    └── dashboard/
        ├── manifest.json
        ├── plugin_api.py     /api/plugins/clawsum-cockpit/*
        └── dist/
            ├── index.js      tab + shell slots
            └── style.css
```

---

## What you get

| Piece | Behavior |
|-------|----------|
| **Theme** `Clawsum Command` | Teal cockpit layout, fonts, crest/logo assets |
| **Tab** `/clawsum` | CEO Brief · Inbox · Archive · Approvals · Health |
| **SOUL.md** | Paperclip + inbox + archive drive; ask clarifying questions |
| **Sidebar / header / footer slots** | HUD KPIs + crest + tagline |
| **Backend** | Brief + inbox + archive + CRM + approvals; links to Boss/OpenClaw/Grafana |
| **Health** | Grafana iframe via `CLAWSUM_GRAFANA_EMBED_URL` |

Governance stays in **Paperclip** + `ops.approvals`. Hermes displays and deep-links.

---

## Install (VPS)

```bash
cd /docker/clawsum

# 1) Hermes web stack (once)
bash scripts/install-hermes-dashboard.sh
bash scripts/hermes-dashboard.sh start

# 2) Overwatch schema (for Approvals / Brief KPIs)
psql -U clawsum -d clawsum -f postgres-init/12-overwatch.sql   # or deploy/postgres-init/...
python3 scripts/seed-business-cells.py

# 3) Cockpit theme + plugin
# Ensure examples are on the VPS (sync repo or copy deploy/examples/hermes-cockpit)
bash scripts/install-hermes-cockpit.sh
bash scripts/hermes-dashboard.sh stop
bash scripts/hermes-dashboard.sh start
```

Browser: Hermes UI → palette → **Clawsum Command** → open **Clawsum** tab. Chat tab remains for JARVIS conversation.

Ops portal: `setup-ops-portal-traefik.sh` so `hermes.${DOMAIN}` is behind the same login wall.

---

## Env for data feeds

Set on the **Paperclip** container (or host env inherited by `hermes dashboard`):

```env
CLAWSUM_BOSS_URL=https://boss.yourdomain.com
CLAWSUM_OPENCLAW_URL=https://clawsum.yourdomain.com
CLAWSUM_GRAFANA_URL=https://grafana.yourdomain.com
# Prefer a kiosk dashboard URL for iframe:
CLAWSUM_GRAFANA_EMBED_URL=https://grafana.yourdomain.com/d/clawsum-health?orgId=1&kiosk
PAPERCLIP_API=http://127.0.0.1:3100/api
PAPERCLIP_COMPANY_ID=your-company-uuid
POSTGRES_HOST=127.0.0.1
POSTGRES_USER=clawsum
POSTGRES_PASSWORD=...
POSTGRES_DB=clawsum
```

After env changes, restart the dashboard process.

### Grafana iframe notes

- Same Traefik basic auth as Hermes helps session cookies.
- If the frame is blank: Grafana may send `X-Frame-Options` / CSP — use “Open Grafana” link, or configure Grafana `allow_embedding = true` and anonymous/kiosk carefully (VPN-only).
- Hybrid UX is intentional: embed for glanceable KPIs; full explore in Grafana.

---

## Replace branding assets

Overwrite SVGs in `assets/` (keep filenames), re-run `install-hermes-cockpit.sh`, hard-refresh the browser.

Or point theme `assets:` URLs at your CDN / MinIO public paths.

---

## Custom logo checklist

1. Drop `logo.svg` / `crest.svg` into `assets/`
2. Re-install cockpit
3. Select **Clawsum Command** theme
4. Confirm header crest + sidebar hero

---

## Related Clawsum docs

- [CEO-COCKPIT.md](../../docs/CEO-COCKPIT.md)
- [HERMES-POLICY.md](../../docs/HERMES-POLICY.md)
- [CHATGPT-ARCHIVE.md](../../docs/CHATGPT-ARCHIVE.md)
- [PAPERCLIP-OVERWATCH.md](../../docs/PAPERCLIP-OVERWATCH.md)
- [BOSS-OPS-PORTAL.md](../../docs/BOSS-OPS-PORTAL.md)
