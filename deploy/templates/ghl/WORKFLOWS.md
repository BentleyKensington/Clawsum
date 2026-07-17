# WORKFLOWS.md — GHL {DISPLAY_NAME}

## Telegram — re-engage summary (Boss request)

When Boss asks for **re-engage summary**, **follow-up list**, or **who to call**:

1. **Read** `REENGAGE.md` in your workspace root with the **read tool** (exact path, one file):
   - `REENGAGE.md`  ← primary (always up to date after audit)
   - fallback: `notes/LATEST-REENGAGE-SUMMARY.md`
2. **Do NOT** use search, browser, or exec for this — read the file directly.
3. Reply with: counts (viable / excluded), top 5–10 by priority, hook + suggested SMS each.
4. Offer to re-run audit if `REENGAGE.md` is stale (>7 days).

**Never** use the search tool for re-engage. **Never** claim unavailable until `read REENGAGE.md` was attempted.

## Standard audit workflow (read-only)

1. Confirm location via MCP (`locations_get-location` or equivalent)
2. Export mental model: pipelines, active workflows, calendars, key custom fields
3. Sample contact/opportunity health (stale 30/60/90d, open opps, unread conversations)
4. Run strategic audit: `python3 /docker/clawsum/scripts/ghl-strategic-audit.py --slug {SLUG}` (Boss or cron)
5. Write `GHL/{OBSIDIAN_FOLDER}/Audits/YYYY-MM-DD-strategic-analysis.md`
6. Open Paperclip tasks for Boss-approved remediation only

## Write operations (Boss approval required)

- Workflow/automation edits
- Bulk tag or pipeline moves
- Calendar or notification changes

Tag issues: `Boss approved GHL writes: yes`
