# Version pinning — OpenClaw, Paperclip, Hermes

**Checked:** 2026-07-01 (VPS `srv.example.com`, `/docker/clawsum`)

---

## Summary

| Component | Deployed (target) | Latest stable | Gap | Recommendation |
|-----------|-------------------|---------------|-----|----------------|
| **OpenClaw** | **`2026.6.10`** | **`2026.6.10`** (`v2026.6.10`) | — | Pin in compose + `.env`; run `upgrade-platform-versions.sh` |
| **Paperclip** | **`latest`** (digest-pinned on VPS) | **`v2026.626.0`** release (2026-06-26) | Version tags **not on GHCR** — use `latest` or `sha-*` | Pin digest after pull; re-run protocol patch |
| **Hermes (Nous)** | **Not installed** in Paperclip container | **`v2026.6.19`** (Hermes Agent v0.17.0) | N/A | Clawsum uses **OpenClaw gateway** for Hermes (`paperclip:hermes` session), not `hermes_local` |

**Previous:** OpenClaw `2026.5.20`, Paperclip `latest` (~2026-05-25).

**Pre-release (not “stable”):** OpenClaw `2026.6.11-beta.*` — skip unless you want beta channel.

---

## OpenClaw

| | |
|--|--|
| **Compose pin** | `ghcr.io/openclaw/openclaw:2026.6.10` |
| **Env override** | `OPENCLAW_IMAGE=...` in `/docker/clawsum/.env` |
| **Latest stable** | [v2026.6.10](https://github.com/openclaw/openclaw/releases/tag/v2026.6.10) |
| **Update docs** | [docs.openclaw.ai/install/updating](https://docs.openclaw.ai/install/updating) |

**Upgrade path (VPS):**

```bash
bash /docker/clawsum/scripts/upgrade-platform-versions.sh
```

Or manual:

```bash
# 1. Edit /docker/clawsum/.env
OPENCLAW_IMAGE=ghcr.io/openclaw/openclaw:2026.6.10
PAPERCLIP_IMAGE=ghcr.io/paperclipai/paperclip:latest

# 2. Recreate services
cd /docker/clawsum
docker compose pull openclaw-gateway
docker compose up -d openclaw-gateway
docker compose --profile orchestration pull paperclip
docker compose --profile orchestration up -d paperclip

# 3. Post-upgrade
bash scripts/fix-paperclip-openclaw-protocol.sh
python3 scripts/paperclip-fix-execution.py --skip-protocol
bash scripts/telegram-smoke-test.sh
```

**Risk:** device pairing, gateway RPC schema, Telegram plugin changes — run during a maintenance window with heartbeats still OFF.

---

## Paperclip

| | |
|--|--|
| **Compose pin** | `ghcr.io/paperclipai/paperclip:latest` |
| **Env override** | `PAPERCLIP_IMAGE=...` in `/docker/clawsum/.env` |
| **Latest release** | [v2026.626.0](https://github.com/paperclipai/paperclip/releases/tag/v2026.626.0) (2026-06-26) |
| **GHCR note** | Semantic `v2026.*` tags often **missing** from GHCR ([#3195](https://github.com/paperclipai/paperclip/issues/3195)); `latest` + digest is reproducible |
| **VPS digest (2026-07-01)** | `sha256:0026a188ec90a4e20b744b53f0f4ea7d5fbe908c95449cafe7b86dd01ac1d7c5` |
| **Known gap** | Some images still ship OpenClaw adapter **protocol v3**; patch script forces **v4** |

**After any Paperclip image change:**

```bash
bash /docker/clawsum/scripts/fix-paperclip-openclaw-protocol.sh
python3 /docker/clawsum/scripts/paperclip-fix-execution.py --skip-protocol
python3 /docker/clawsum/scripts/fix-paperclip-pairing-scopes.py   # if pairing errors return
```

**Recommended pin (when upgrading):**

```yaml
image: ghcr.io/paperclipai/paperclip:v2026.626.0
```

Verify tag exists on GHCR before pinning ([issue #3195](https://github.com/paperclipai/paperclip/issues/3195) — some version tags may lag `latest`).

---

## Hermes (Clawsum policy)

Clawsum **does not** run standalone Hermes Agent as the primary path.

| Mode | Status |
|------|--------|
| **Production** | `Clawsum Hermes` → `openclaw_gateway` → admin session `paperclip:hermes` → **Codex / ChatGPT Plus** |
| **Legacy** | `hermes_local` + `install-hermes-in-paperclip.sh` — **not installed** on VPS (`hermes` CLI missing in container) |
| **Latest Hermes Agent** | [v2026.6.19](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.6.19) (v0.17.0) |

If you later want native Hermes in Paperclip:

```bash
bash /docker/clawsum/scripts/install-hermes-in-paperclip.sh
docker exec clawsum-paperclip-1 hermes version
```

That is **optional** and bills via API unless wired through OpenClaw — see [HERMES-POLICY.md](./HERMES-POLICY.md).

---

## Version check commands (VPS)

```bash
docker exec clawsum-openclaw-gateway-1 node dist/index.js --version
docker images | grep -E 'openclaw|paperclip'
docker exec clawsum-paperclip-1 hermes --version 2>/dev/null || echo "Hermes CLI not installed (expected for Codex path)"
curl -s https://api.github.com/repos/openclaw/openclaw/releases/latest | grep tag_name
curl -s https://api.github.com/repos/paperclipai/paperclip/releases/latest | grep tag_name
curl -s https://api.github.com/repos/NousResearch/hermes-agent/releases/latest | grep tag_name
```

---

## When to upgrade

1. Boss backlog cleared and heartbeats policy agreed.
2. Snapshot `/docker/clawsum/data/.openclaw` and `paperclip-data`.
3. Upgrade **OpenClaw** first → smoke Telegram + one manual gateway agent call.
4. Upgrade **Paperclip** → re-apply protocol patch → verify heartbeat (one agent, one task).
5. Keep heartbeats OFF until Boss approves resuming work.
