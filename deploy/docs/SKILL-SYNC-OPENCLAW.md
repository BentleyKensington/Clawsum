# Paperclip skill sync vs OpenClaw

## The blocker

Agents on adapter **`openclaw_gateway`** report:

```text
supported: false
mode: "unsupported"
warning: "This adapter does not implement skill sync yet."
```

Paperclip can store a company skill, but it **does not mount** it onto the OpenClaw runtime. That is an adapter gap — not a problem with skill content (e.g. Closebot).

## Workaround (filesystem mount)

Install skills into the OpenClaw workspace skills tree (bound into the gateway container):

```bash
ssh root@76.13.97.82
bash /docker/clawsum/scripts/install-closebot-skill-openclaw.sh
```

That copies `closebot-api-operator` →:

- `/docker/clawsum/data/.openclaw/workspace/skills/closebot-api-operator`
- `/docker/clawsum/paperclip-data/.hermes/skills/integrations/closebot-api-operator`

## CloseBot API key

Edit env:

```bash
nano /docker/clawsum/.env
```

```bash
CLOSEBOT_API_KEY=your_key_here
# optional fallback name also read by the helper:
# X_CB_KEY=your_key_here
```

HTTP header CloseBot expects: **`X-CB-KEY`**.

Then restart gateway so the container picks up the var:

```bash
cd /docker/clawsum && docker compose up -d openclaw-gateway
```

Helper: `…/closebot-api-operator/scripts/closebot_request.py` reads `CLOSEBOT_API_KEY` or `X_CB_KEY` and sends `X-CB-KEY`.
