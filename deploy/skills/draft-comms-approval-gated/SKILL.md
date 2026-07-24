---
name: draft-comms-approval-gated
description: Drafts email/SMS/outreach for a cell and stops before send pending Gerald approval. Use whenever outbound messaging is requested.
agents: [comms, ghl, admin, hermes]
cells: ["*"]
tier_autonomous: 1
credentials: [cell-specific]
approval_actions: [send_email, send_sms, send_outreach, customer_comms]
---

# Draft comms (approval-gated)

1. Confirm cell + audience.
2. Draft message in chat or Paperclip description.
3. Create Tier 2 `ops.approvals` with full draft text.
4. **Do not send** until approved.
5. After approve, OpenClaw cell agent executes send with cell credentials only.
