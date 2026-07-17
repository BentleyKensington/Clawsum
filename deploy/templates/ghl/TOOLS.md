# TOOLS.md — GHL {DISPLAY_NAME}

## Allowed

- **read** — exact file paths only
- **write** — workspace + Obsidian (account folder only)
- **GHL MCP** — CRM read/write per Boss approval

## Denied (will fail in Telegram)

search · grep · glob · browser · exec

## Re-engage summary paths

```
REENGAGE.md
/home/node/.openclaw/workspace-{AGENT_ID}/REENGAGE.md
notes/REENGAGE.md
```

**Example:** read `REENGAGE.md` then reply with top leads + suggested SMS.

Full audit reports (Obsidian, read-only):

```
/home/node/obsidian/GHL/{OBSIDIAN_FOLDER}/Recommendations/LATEST-REENGAGE-SUMMARY.md
/home/node/obsidian/GHL/{OBSIDIAN_FOLDER}/Recommendations/*-reengage-leads.md
```

## Strategic audit (Boss or cron — not via Telegram exec)

```bash
python3 /docker/clawsum/scripts/ghl-strategic-audit.py --slug {SLUG} --use-llm
```

Refreshes `REENGAGE.md` automatically.
