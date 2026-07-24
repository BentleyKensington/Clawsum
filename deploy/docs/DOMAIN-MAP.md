# Clawsum.com domain & subdomain map

**VPS IP:** `76.13.97.82`  
**Registrar:** Porkbun (`clawsum.com`)  
**Edge:** Traefik + Let's Encrypt on the reference VPS

---

## Optimal host set (keep this small)

| Host | Public? | Purpose |
|------|---------|---------|
| **clawsum.com** | Yes | Sales funnel / marketing |
| **www.clawsum.com** | Yes | → same funnel |
| **hermes.clawsum.com** | Auth | JARVIS / Hermes CEO UI (primary ops face) |
| **boss.clawsum.com** | Auth | Paperclip Boss UI (tasks / approvals) |
| **openclaw.clawsum.com** | Auth | OpenClaw Control UI (gateway, channels) |
| **grafana.clawsum.com** | Auth | Metrics / health |
| **login.clawsum.com** | Auth | Ops launcher — links into Hermes/Boss/OpenClaw/Grafana |
| **connect.clawsum.com** | Auth | Integrations / OAuth / “connect systems” hub |
| **api.clawsum.com** | Auth later | Future CEO/overwatch API |
| **mail.clawsum.com** | DNS only* | Reserved for mail gateway; apex **MX stays Porkbun** until you cut over |

\*Do not put a public webmail UI on `mail` until spam/auth is designed. A-record reserves the name.

### Intentionally not created

| Idea | Why skip |
|------|----------|
| `cockpit.*` | Redundant with `hermes.*` |
| `status.*` | Use Grafana + daily Telegram for now |
| `*.clawsum.com` wildcard → VPS | Too broad; explicit hosts only |
| Discord/Telegram as DNS | Not HTTP |

---

## Auth model

- **Marketing** (`clawsum.com`, `www`): public HTTPS, no basic auth  
- **Ops hosts** (`hermes`, `boss`, `openclaw`, `grafana`, `login`, `connect`, `api`): Traefik basic auth (ops portal) → app login where applicable  

VPN/Tailscale still recommended long-term; Traefik wall is the minimum.

---

## Porkbun notes

Prior parking used:

- `ALIAS clawsum.com → uixie.porkbun.com`
- `CNAME *.clawsum.com → uixie.porkbun.com`

Those **must be removed** so apex + subdomains can point at the VPS. Apex **MX** (Porkbun forwarding) and SPF can remain until you migrate email.

**API keys:** store only in `/docker/clawsum/.env` on the VPS (or local shell env). Never commit. **Rotate** any key pasted into chat.

```bash
# On a secure machine / VPS
export PORKBUN_API_KEY=...
export PORKBUN_SECRET_KEY=...
export CLAWSUM_VPS_IP=76.13.97.82
python3 scripts/porkbun-sync-dns.py
```

---

## Apply Traefik after DNS

```bash
cd /docker/clawsum
# marketing site + ops hosts for clawsum.com
bash scripts/setup-clawsum-domains.sh
```

---

## Related

- [BOSS-OPS-PORTAL.md](./BOSS-OPS-PORTAL.md)
- [CEO-COCKPIT.md](./CEO-COCKPIT.md)
- `sites/clawsum-com/` — funnel static site
