# Boss ops portal — public domain + unified login

One secure HTTPS entry for **Hermes UI** (CEO chat), **Boss UI**, **OpenClaw Control UI**, and **Grafana** — without exposing Postgres, Prometheus, or raw gateway ports.

**Primary browser face (preferred):** Hermes UI at `hermes.${DOMAIN}` — see [CEO-COCKPIT.md](./CEO-COCKPIT.md) and [HERMES-POLICY.md](./HERMES-POLICY.md).

**Paperclip Boss UI** remains the task / approval control plane. **Clawsum Hermes** (assignee) is still headless via OpenClaw (`paperclip:hermes`) for long jobs only.

---

## Architecture

```text
                    Internet (HTTPS :443)
                            │
                     Traefik (host network)
                     ┌──────┴──────┐
                     │  Login wall  │  ← Tier 1: Traefik basic auth OR Authelia forwardAuth
                     └──────┬──────┘
     ┌──────────┬───────────┼───────────┬──────────┐
     ▼          ▼           ▼           ▼          ▼
 hermes.*    boss.*    clawsum.*   grafana.*   (future cockpit.*)
     │          │           │           │
     ▼          ▼           ▼           ▼
  :9119      :3100      gateway      :3000
 Hermes UI  Paperclip   OpenClaw     Grafana
 (CEO chat) (tasks)     Control UI   (metrics)
```

| Surface | Hostname | Backend | App-level auth |
|---------|----------|---------|----------------|
| **Hermes UI** | `hermes.${DOMAIN}` | `127.0.0.1:9119` | Traefik wall (+ Hermes session if any) |
| **Boss UI** | `boss.${DOMAIN}` | `127.0.0.1:3100` | Paperclip **Better Auth** |
| **OpenClaw Control UI** | `clawsum.${DOMAIN}` | gateway UI | Trusted-proxy or gateway token |
| **Grafana** | `grafana.${DOMAIN}` | `127.0.0.1:3000` | Grafana login |

---

## Recommended approach (two layers)

### Layer 1 — Traefik login wall (same for all hosts)

Pick one:

| Method | Best for | One login? |
|--------|----------|------------|
| **Traefik basic auth** | Fastest; Boss-only team | Same password per subdomain (one prompt each) |
| **Authelia** | Email + 2FA; production | Yes — session cookie across subdomains |
| **Cloudflare Access** | No VPS auth service | Yes — at Cloudflare edge |

Use `deploy/scripts/setup-ops-portal-traefik.sh` for **basic auth** (Tier 1).

### Layer 2 — App auth (inside the wall)

| App | What Boss still does |
|-----|----------------------|
| **Hermes UI** | Chat as JARVIS; do not paste secrets into chat |
| **Boss UI** | Sign in with Paperclip user. Set `PAPERCLIP_PUBLIC_URL=https://boss…` |
| **OpenClaw** | With **trusted-proxy**: no gateway token. Without: paste `OPENCLAW_GATEWAY_TOKEN` once |
| **Grafana** | `admin` + `GRAFANA_ADMIN_PASSWORD` unless auth proxy |

---

## Quick start (basic auth + Hermes primary)

### 1. DNS

| Type | Name | Value |
|------|------|--------|
| A | `hermes` | VPS public IP |
| A | `boss` | VPS public IP |
| A | `clawsum` | VPS public IP |
| A | `grafana` | VPS public IP (optional) |

### 2. `.env` on VPS

```env
TRAEFIK_HOST=yourdomain.com
HERMES_UI_HOST=hermes.yourdomain.com
BOSS_UI_HOST=boss.yourdomain.com
OPENCLAW_UI_HOST=clawsum.yourdomain.com
GRAFANA_UI_HOST=grafana.yourdomain.com
PAPERCLIP_PUBLIC_URL=https://boss.yourdomain.com

BOSS_OPS_AUTH_USER=boss
BOSS_OPS_AUTH_PASSWORD=change_me_strong
```

### 3. Start Hermes dashboard + portal

```bash
cd /docker/clawsum
bash scripts/install-hermes-dashboard.sh
bash scripts/hermes-dashboard.sh start

HERMES_HOST=hermes.yourdomain.com \
BOSS_HOST=boss.yourdomain.com \
OPENCLAW_HOST=clawsum.yourdomain.com \
GRAFANA_HOST=grafana.yourdomain.com \
bash scripts/setup-ops-portal-traefik.sh
```

### 4. OpenClaw Control UI behind the same wall (trusted-proxy)

```bash
python3 /docker/clawsum/scripts/patch-control-ui-trusted-proxy.py
cd /docker/clawsum && docker compose restart openclaw-gateway
```

### 5. Verify

```bash
curl -u boss:PASSWORD -sS -o /dev/null -w '%{http_code}\n' https://hermes.yourdomain.com/
curl -u boss:PASSWORD -sS -o /dev/null -w '%{http_code}\n' https://boss.yourdomain.com/api/health
curl -u boss:PASSWORD -sS -o /dev/null -w '%{http_code}\n' https://clawsum.yourdomain.com/healthz
```

Browser order: **Hermes** (chat) → **Boss** (CLA-41 / tasks) → **Grafana** (health) → **Control UI** (channels).

---

## Hermes “dashboard”

| What you want | Where |
|---------------|--------|
| Daily CEO chat | **Hermes UI** `https://hermes…` |
| Assign a long Hermes job | Boss UI → assignee **Clawsum Hermes** + `Boss authorized Hermes: yes` |
| Track task progress | Boss UI board + activity |
| Approvals / business cells | [PAPERCLIP-OVERWATCH.md](./PAPERCLIP-OVERWATCH.md) + Boss UI |

---

## Production: Authelia (single sign-on)

For one login across all subdomains:

1. Deploy [Authelia](https://www.authelia.com/) on the VPS (or use Cloudflare Access).
2. Replace `boss-ops-auth` basic auth middleware with `forwardAuth` → Authelia.
3. Authelia sets `Remote-User` → Traefik copies to `X-Forwarded-User`.
4. Run `patch-control-ui-trusted-proxy.py`.
5. Configure Paperclip Better Auth separately — or rely on Traefik + `local_trusted` if threat model allows.

Authelia is **not** in compose today; treat as instance overlay when you outgrow basic auth.

---

## Security checklist

- [ ] All admin UIs on HTTPS only (Traefik Let's Encrypt)
- [ ] Traefik login wall on **hermes**, **boss**, **clawsum**, **grafana**
- [ ] Hermes dashboard bound to `127.0.0.1` only; Traefik proxies
- [ ] `PAPERCLIP_PUBLIC_URL` matches browser URL exactly
- [ ] `OPENCLAW_GATEWAY_TOKEN` rotated; not committed to git
- [ ] OpenClaw `gateway.trustedProxies` lists only Traefik
- [ ] Firewall: only `:22`, `:80`, `:443` public
- [ ] SSH tunnel fallback documented for outages

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Hermes 502 | `hermes-dashboard.sh status` / `start`; confirm :9119 on loopback |
| Boss UI cookie / redirect loop | `PAPERCLIP_PUBLIC_URL` must be `https://boss…` with no trailing slash |
| OpenClaw 401 / pairing required | Run `patch-control-ui-trusted-proxy.py` |
| Daily Telegram at 2am | Re-run `install-daily-report-cron.sh` — needs `CRON_TZ=America/Chicago` ([RESUME-POLICY.md](./RESUME-POLICY.md)) |
| Double login annoyance | Upgrade to Authelia or Cloudflare Access |

---

## Related

- [CEO-COCKPIT.md](./CEO-COCKPIT.md) — shell vs portal
- [RESUME-POLICY.md](./RESUME-POLICY.md) — unpause safely
- [BOSS-UI-PUBLIC-DOMAIN.md](./BOSS-UI-PUBLIC-DOMAIN.md)
- [BOSS-ACCESS-GUIDE.md](./BOSS-ACCESS-GUIDE.md)
- [HERMES-POLICY.md](./HERMES-POLICY.md)
- OpenClaw: [Trusted proxy auth](https://docs.openclaw.ai/gateway/trusted-proxy-auth)
