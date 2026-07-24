---
name: chatgpt-archive
description: Imports ChatGPT exports, classifies personal vs business, links Paperclip issues, and builds proactive briefs. Use for Gerald history archive — never dump into Hermes memory.
agents: [admin, data, hermes]
cells: [clawsum-platform, personal-admin]
tier_autonomous: 1
credentials: [POSTGRES_*, PAPERCLIP_*]
approval_actions: [approved_for_hermes]
---

# ChatGPT archive

```bash
bash /docker/clawsum/scripts/run-chatgpt-archive.sh /path/to/export.zip
python3 /docker/clawsum/scripts/classify-chatgpt-archive.py --all
python3 /docker/clawsum/scripts/link-archive-to-paperclip.py
python3 /docker/clawsum/scripts/archive-proactive-brief.py --markdown
```

## Hard rules

- `approved_for_hermes` default false.
- Personal scope → not business agents.
- Docs: `deploy/docs/CHATGPT-ARCHIVE.md`
