---
name: credential-hygiene
description: Audits credential exposure, rotation needs, and secret-handling rules across cells. Use after paste incidents, onboarding, or security review.
agents: [admin, coding]
cells: [clawsum-platform]
tier_autonomous: 0
credentials: []
approval_actions: [credential_rotate]
---

# Credential hygiene

## Rules

- Never commit `.env`, client secrets, PITs.
- Rotate any key pasted in chat (Porkbun, Gmail, etc.).
- Skills list prefixes only — not values.
- Rotation itself = Tier 2–3 human with coding support.
- See `CREDENTIALS-EXCLUSION.md` if present.
