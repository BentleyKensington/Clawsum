# Boss UI — public domain (no SSH tunnel)

Expose **Paperclip Boss UI** at a HTTPS hostname (e.g. `https://boss.yourdomain.com`) instead of `ssh -L 3100:127.0.0.1:3100`.

**Today:** Paperclip listens on **`127.0.0.1:3100`** only (`local_trusted`, private). That is correct — Traefik on the VPS forwards public HTTPS to that loopback port.

**OpenClaw Control UI** is a separate hostname (`clawsum.${TRAEFIK_HOST}`). Use a **second subdomain** for Boss UI.

---

## Architecture

```text
Browser  →  DNS  →  VPS :443 (Traefik, host network)
                         │
                         └─► http://127.0.0.1:3100  (Paperclip, host network)
```

| Component | Role |
|-----------|------|
| **Traefik** | TLS (Let’s Encrypt), routing, optional basic auth / IP allowlist |
| **Paperclip** | Boss UI app — stays on loopback; not published to `0.0.0.0` |
| **`PAPERCLIP_PUBLIC_URL`** | Must match the public URL (cookies / Better Auth callbacks) |

Traefik stack: `/docker/traefik/` (host network, Docker provider).  
Clawsum stack: `/docker/clawsum/` (Paperclip profile `orchestration`).

---

## 1. Choose a hostname

Examples:

| Hostname | When to use |
|----------|-------------|
| `boss.srv.example.com` | Quick test on existing Hostinger VPS hostname |
| `boss.clawsum.com` | Production custom domain |

Pick one FQDN and use it **everywhere** below (`BOSS_HOST`).

---

## 2. DNS

At your DNS provider:

| Type | Name | Value |
|------|------|--------|
| **A** | `boss` | VPS public IP (`YOUR_VPS_IP` for srv.example.com) |
| or **CNAME** | `boss` | `srv.example.com.hstgr.cloud` |

Wait for propagation, then:

```bash
dig +short boss.yourdomain.com
```

---

## 3. Clawsum `.env`

Edit `/docker/clawsum/.env`:

```env
# Public Boss UI URL (exact scheme + host, no trailing slash)
PAPERCLIP_PUBLIC_URL=https://boss.yourdomain.com

# Optional: used by Traefik router label examples below
BOSS_UI_HOST=boss.yourdomain.com
TRAEFIK_HOST=yourdomain.com
```

**Required:** `BETTER_AUTH_SECRET` must already be set (non-empty). If Boss UI auth behaves oddly after cutover, generate a new secret once and restart Paperclip.

Restart Paperclip after changing `PAPERCLIP_PUBLIC_URL`:

```bash
cd /docker/clawsum
docker compose --profile orchestration up -d paperclip
```

Verify locally:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3100/api/health
```

---

## 4. Traefik route to Paperclip

Paperclip has **no Docker Traefik labels** (it uses `network_mode: host`). Traefik runs on **host network**, so it can proxy to **`http://127.0.0.1:3100`**.

### Option A — File provider (recommended)

Create `/docker/traefik/dynamic/boss-ui.yml`:

```yaml
http:
  routers:
    clawsum-boss:
      rule: Host(`boss.yourdomain.com`)
      entryPoints:
        - websecure
      service: clawsum-boss
      tls:
        certResolver: letsencrypt
      # Optional: require HTTP basic auth (see §5)
      # middlewares:
      #   - boss-auth

  services:
    clawsum-boss:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:3100
```

Add the file provider to `/docker/traefik/docker-compose.yml` under `traefik` `command`:

```yaml
      - --providers.file.directory=/dynamic
      - --providers.file.watch=true
```

Mount the directory:

```yaml
    volumes:
      - traefik-letsencrypt:/letsencrypt
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./dynamic:/dynamic:ro
```

Then:

```bash
mkdir -p /docker/traefik/dynamic
# create boss-ui.yml as above
cd /docker/traefik
docker compose up -d
```

### Option B — Docker labels (sidecar in Clawsum compose)

Add a minimal service whose only job is Traefik routing (Traefik resolves `127.0.0.1` from the **host** perspective):

```yaml
  boss-ui-route:
    image: traefik/whoami:v1.10.2
    restart: unless-stopped
    networks: [clawsum]
    labels:
      - traefik.enable=true
      - traefik.http.routers.clawsum-boss.rule=Host(`boss.${TRAEFIK_HOST:-localhost}`)
      - traefik.http.routers.clawsum-boss.entrypoints=websecure
      - traefik.http.routers.clawsum-boss.tls.certresolver=letsencrypt
      - traefik.http.services.clawsum-boss.loadbalancer.server.url=http://127.0.0.1:3100
    profiles: ["orchestration"]
```

```bash
cd /docker/clawsum
docker compose --profile orchestration up -d boss-ui-route
```

Replace `boss.${TRAEFIK_HOST}` with a fixed host if you prefer (`boss.yourdomain.com`).

---

## 5. Security (do not skip)

Boss UI in **`local_trusted`** mode is meant for a private VPS. Putting it on the internet requires extra controls:

| Control | Purpose |
|---------|---------|
| **HTTPS only** | Traefik already redirects `:80` → `:443` |
| **Traefik basic auth** | Simple shared password in front of Boss UI |
| **Cloudflare Access / Tailscale** | Stronger identity gate |
| **IP allowlist** | Traefik `ipWhiteList` middleware — home/office IPs only |
| **Separate subdomain** | Do not merge with OpenClaw Control UI on one host |

### Example: Traefik basic auth

```bash
# Install htpasswd if needed: apt-get install apache2-utils
htpasswd -nbB boss 'YOUR_STRONG_PASSWORD' | sed -e 's/\$/\$\$/g'
```

Append to `/docker/traefik/dynamic/boss-ui.yml`:

```yaml
  middlewares:
    boss-auth:
      basicAuth:
        users:
          - "boss:$$2y$$05$$...."   # output from htpasswd command

  routers:
    clawsum-boss:
      middlewares:
        - boss-auth
```

Traefik reloads file provider automatically when `watch=true`.

---

## 6. Verify

From your PC (no SSH):

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://boss.yourdomain.com/api/health
```

Expect **200**. Open in browser:

**https://boss.yourdomain.com**

| Check | Expected |
|-------|----------|
| Page loads | Boss UI / Paperclip |
| Login / session | Works with `PAPERCLIP_PUBLIC_URL` set to same origin |
| Heartbeats | Paperclip still reaches OpenClaw at `http://127.0.0.1:48166` (unchanged) |

Prometheus probe (optional): add `https://boss.yourdomain.com/api/health` to blackbox targets later.

---

## 7. Keep SSH tunnel as fallback

If Traefik or DNS breaks:

```bash
ssh -L 3100:127.0.0.1:3100 clawsum
# http://localhost:3100
```

Tunnel does not require `PAPERCLIP_PUBLIC_URL` changes; public URL is only for browser access without SSH.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| **502 / Bad Gateway** | Paperclip down: `docker compose --profile orchestration ps paperclip` |
| **Connection refused** | Confirm `127.0.0.1:3100`: `ss -tlnp \| grep 3100` |
| **Wrong redirect / cookie errors** | `PAPERCLIP_PUBLIC_URL` must exactly match browser URL (`https://…`) |
| **Cert not issued** | DNS must point to VPS; port 80 open for HTTP-01 challenge |
| **OpenClaw works, Boss doesn’t** | OpenClaw has Traefik labels; Boss needs file provider or sidecar (§4) |
| **`.env` PORT=48165` leaked into Paperclip** | Compose pins `PORT=3100` — do not use `env_file` on Paperclip service |

---

## Related docs

- [BOSS-OPS-PORTAL.md](./BOSS-OPS-PORTAL.md) — **recommended** unified portal (Boss + OpenClaw + Grafana behind one Traefik login)
- [BOSS-UI-AND-MONITORING.md](./BOSS-UI-AND-MONITORING.md) — what Boss UI is for, tasks, 7am report
- [PAPERCLIP-SETUP.md](./PAPERCLIP-SETUP.md) — wiring agents + Hermes
- OpenClaw Control UI (separate host): `https://clawsum.${TRAEFIK_HOST}/` — see gateway `controlUi.allowedOrigins`

---

## Checklist

- [ ] DNS `boss.*` → VPS IP  
- [ ] `PAPERCLIP_PUBLIC_URL=https://boss.…` in `/docker/clawsum/.env`  
- [ ] Traefik route → `http://127.0.0.1:3100` (file provider or sidecar)  
- [ ] TLS certificate issued (Let’s Encrypt)  
- [ ] Basic auth or IP allowlist (recommended)  
- [ ] Restart Paperclip + Traefik  
- [ ] Browser test: `/api/health` and Boss UI login  
