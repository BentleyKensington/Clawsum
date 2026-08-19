# MEMORY.md — ranked pending queue

Update statuses as work moves. Hermes reads this on session start and may rewrite ranks after wrap-up.
Live systems of record remain Paperclip + `ops.*` — this file is the **executive ranking**, not a shadow DB.

| Rank | Item | Source | Status | Owner | Next |
|------|------|--------|--------|-------|------|
| 1 | Review `needs_boss` inbox analyses | Inbox / ops.emails | open | Gerald + Clawsum | Open Inbox; decide or assign |
| 2 | Clear pending overwatch approvals | ops.approvals | open | Gerald | Approve / reject / revise |
| 3 | Paperclip blocked / awaiting Boss | Paperclip | open | Gerald | Unblock or reassign |
| 4 | Confirm Gmail sync healthy | ops.email_sync_state | watch | Admin / Data | Check Grafana sync age |
| 5 | Heartbeats gated (CLA-41 / RESUME-POLICY) | Paperclip | blocked | Gerald | Do not enable until policy met |

## Notes

- Promote durable facts to Obsidian only when Gerald confirms.
- Cell-scoped work stays with the owning agent (GHL / RE / Coding / …).
