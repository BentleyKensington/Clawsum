---
name: rocco-ring-official
description: Manage Gerald's Ring cameras via the official Ring Appstore / Private Use Apps API only. No reverse engineering of Ring private protocols.
agents: [rocco, admin]
cells: [clawsum-platform]
tier_autonomous: 0
credentials: [RING_CLIENT_ID, RING_CLIENT_SECRET, RING_REFRESH_TOKEN]
approval_actions: [ring_config_change]
---

# Ring — official API only

See [ROCCO-SECURE.md](../../docs/ROCCO-SECURE.md).

Portal: https://developer.amazon.com/docs/ring/get-started.html  
API base: `https://api.amazonvision.com` (OAuth 2.0, JSON:API).  
**Private Use Apps** — allowlist up to 5 Ring accounts; no public listing required.

## Hard limits

- Do **not** implement unofficial doorbell protocol reverse-engineering (including the Reddit Claude-Code writeup).
- Do **not** use stolen/session cookies or undocumented private APIs.
- Home Assistant **official** Ring integration is an allowed interim event bridge.

## Phase 1 (when OAuth exists)

Device discovery, status, webhook subscription for ding/motion. Notify Boss. Config writes = Tier 2.

## Phase 2

Official media/live if Partner API documents it for the app. Desktop viewer consumes **official** stream URLs only. 24/7 local archive only if the API allows continuous media; otherwise use Ring Protect cloud + official clip download to MinIO.

## If credentials missing

Tell Boss the portal steps. Do not scrape the Ring consumer app.
