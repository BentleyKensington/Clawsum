# SECURITY.md — Clawsum company pack

- Secrets live in `/docker/clawsum/.env` / vault — never in SOUL, MEMORY, chat, or git.
- GHL PITs are cell-scoped; Admin may see summaries, not raw PITs in chat.
- Authelia SSO guards ops hosts; do not disable for convenience.
- Rotate any credential pasted into chat history.
- Production apply, DNS, and send paths require Tier 2 approval visibility.
