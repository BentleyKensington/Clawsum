---
name: vapi-account-ops
description: Manage the VAPI org via REST (Bearer VAPI_API_KEY). List assistants/calls/numbers. Create, outbound, buy number = Tier 2.
agents: [vapi, vocalitic, admin]
cells: [vocalitic, clawsum-platform]
tier_autonomous: 1
credentials: [VAPI_API_KEY]
approval_actions: [outbound_call, buy_number, assistant_mutate]
---

# VAPI account ops

Docs: https://docs.vapi.ai/ · API: https://api.vapi.ai · Key: https://dashboard.vapi.ai/org/api-keys

```env
VAPI_API_KEY=
VAPI_BASE_URL=https://api.vapi.ai
```

```bash
python3 /docker/clawsum/scripts/vapi_request.py GET /assistant
python3 /docker/clawsum/scripts/vapi_request.py GET /phone-number
python3 /docker/clawsum/scripts/vapi_request.py GET /call
```

## Autonomous

List assistants, phone numbers, recent calls, logs. Summarize quality / failures.

## Tier 2

PATCH/POST assistant, `POST /call` outbound, purchase numbers, campaigns, delete.

Transcriber/voice: prefer Deepgram Flux when Lab scorecard says so; don’t swap live assistants without approval.

## Escalation

Missing key → Boss. Never put the Bearer token in chat.
