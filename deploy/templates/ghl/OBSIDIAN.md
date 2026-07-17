# OBSIDIAN.md — {AGENT_ID}

## Vault path (container)

`/home/node/obsidian/GHL/{OBSIDIAN_FOLDER}/`

## Scope

GHL CRM deliverables for **{DISPLAY_NAME}** only — audits, recommendations, runbooks.

## Rules

- **Write here:** durable notes Boss should read in Obsidian.
- **Do not write:** secrets, API keys, PIT tokens.
- **Never** write into other agents' GHL folders — only **{OBSIDIAN_FOLDER}/**.
- Promote finished work from workspace `notes/` into this folder.

## Subfolders

- `Audits/` — automation reviews
- `Recommendations/` — lost opportunities, remediation proposals
- `Recommendations/LATEST-REENGAGE-SUMMARY.md` — **Telegram quick summary** (updated each strategic audit)

## Instance overlays (optional)

Vertical playbooks (e.g. REI) belong in the instance Obsidian vault, not the generic template repo.
See `deploy/examples/instance-overlays/` for reference copies.
