---
name: openclaw-agent-config
description: Configures OpenClaw gateway agents, skills (e.g. gog), and session bindings for Paperclip assignees. Use when wiring agents or enabling Gmail tools in Control UI.
agents: [coding, admin]
cells: [clawsum-platform]
tier_autonomous: 1
credentials: [OPENCLAW_*, GOG_*, GMAIL_*]
approval_actions: [production_deploy]
---

# OpenClaw agent config

```bash
python3 /docker/clawsum/scripts/enable-gog-skill.py
bash /docker/clawsum/scripts/install-gog-gmail-openclaw.sh   # if present
python3 /docker/clawsum/scripts/wire-paperclip-clawsum.py
```

Keep cell credentials scoped per agent. Gateway config edits on prod = Tier 2.
