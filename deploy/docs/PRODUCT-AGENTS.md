# Product agents — Vocalitic, AcceptAI, CloseBot, VAPI, Printful, Shopify

**Wiring bug (fixed this sprint):** CloseBot / Printful / Shopify / AcceptAI had Discord + persona seed, but **`configure-openclaw.py` rewrote `agents.list` without them** and **`wire-paperclip-clawsum.py` did not create Paperclip assignees**. Coding’s `vocalitic-health` is a skill, not a product company.

---

## Vocalitic (`vocalitic`)

**Purpose:** own the voice-AI product: codebase, dashboard, SignalWire/STT/TTS/LLM health, recommend changes for Gerald.

**Codebase:** local tree **`C:\APPS\V1m12`** (workspace `V1m12.code-workspace`). Set on VPS if a copy is mounted there:

```env
VOCALITIC_CODEBASE_PATH=C:\APPS\V1m12
VOCALITIC_SSH_HOST=69.62.64.214
VOCALITIC_SSH_USER=root
VOCALITIC_SSH_PORT=22
VOCALITIC_SSH_KEY_PATH=    # on VPS or this PC, never in git
VOCALITIC_DASHBOARD_URL=https://app1.vocalitic.com
VOCALITIC_HEALTH_URL=
```

Remote layout (`DEPLOY.md`): Traefik `/opt/traefik`, Vocalitic app1 `/opt/apps/app1` (build context `v1m12/`). Dashboard server defaults to port **9080**. Read-only SSH:

```bash
ssh -i "$VOCALITIC_SSH_KEY_PATH" -p "$VOCALITIC_SSH_PORT" \
  "$VOCALITIC_SSH_USER@$VOCALITIC_SSH_HOST" \
  'hostname; docker ps --format "{{.Names}} {{.Status}}"; ls /opt/apps/app1'
```

Never print the key. Mutating containers / deploys = **Tier 2**.

**Skills:** `vocalitic-product-ops`, `vocalitic-health`, `product-ssh-ops`, `deepgram-voice-eval` (with LLM Lab).

**Workflow:** read SOUL + repo README in `v1m12` → check dashboard/health → observations in Obsidian `Vocalitic/` → Paperclip for approved changes.

---

## AcceptAI (`acceptai`)

Same pattern as Vocalitic for the AcceptAI / FastBuy **app**, not just ad copy.

```env
ACCEPTAI_CODEBASE_PATH=
ACCEPTAI_SSH_HOST=
ACCEPTAI_SSH_USER=
ACCEPTAI_SSH_PORT=22
ACCEPTAI_SSH_KEY_PATH=
ACCEPTAI_DASHBOARD_URL=
ACCEPTAI_API_BASE=
ACCEPTAI_API_KEY=          # if a management API exists
```

**Skills:** `acceptai-product-ops`, `commerce-fastbuy`, `product-ssh-ops`.

Comms still drafts customer copy; AcceptAI agent owns **the product runtime**.

---

## CloseBot (`closebot`)

Docs: https://developers.closebot.com/ · Base `https://api.closebot.com` · Header `X-CB-KEY`.

Key: https://app.closebot.com/settings?tab=keys → `CLOSEBOT_API_KEY` on VPS.

**Autonomous:** `GET /agency/current`, list bots/sources/leads, metrics.  
**Tier 2:** send message to lead, publish bot, billing refill, delete.

Helper: `skills/closebot-api-operator/scripts/closebot_request.py`

Paperclip adapter still does **not** sync skills — filesystem install required.

---

## VAPI (`vapi`)

Docs: https://docs.vapi.ai/ · Base `https://api.vapi.ai` · `Authorization: Bearer $VAPI_API_KEY`

Key: https://dashboard.vapi.ai/org/api-keys

**Autonomous:** list assistants, calls, phone numbers, logs.  
**Tier 2:** create/update assistant, outbound `POST /call`, buy numbers, campaigns.

Helper: `scripts/vapi_request.py`

---

## Printful (`printful`) + Shopify (`shopify`)

Status before this sprint: lanes exist; **no API runbooks**.

```env
PRINTFUL_API_TOKEN=        # Printful API (store token)
SHOPIFY_STORE=             # example.myshopify.com
SHOPIFY_ADMIN_TOKEN=       # Admin API, least privilege
```

Printful catalog/orders = read Tier 1; live product/price/sync = Tier 2.  
Shopify theme/payment/shipping = Tier 2.

**Google Photos:** Picker only (see [GOOGLE-PHOTOS-ACCESS.md](./GOOGLE-PHOTOS-ACCESS.md)) for mockups on `clawsums@gmail.com`.

---

## SSH skill shared

`product-ssh-ops` is the only place that documents jump-host, `StrictHostKeyChecking`, and “recommend vs apply.” Vocalitic and AcceptAI both load it.
