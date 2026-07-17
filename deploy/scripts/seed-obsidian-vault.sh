#!/usr/bin/env bash
# Seed Obsidian vault content + OBSIDIAN.md in each agent workspace.
set -euo pipefail

BASE=/docker/clawsum/data/.openclaw
OBS=/docker/clawsum/obsidian

write_obsidian_md() {
  local agent=$1 folder=$2 scope=$3
  cat > "$BASE/workspace-${agent}/OBSIDIAN.md" <<EOF
# OBSIDIAN.md — ${agent}

## Vault path (container)

\`/home/node/obsidian/${folder}/\`

## Scope

${scope}

## Rules

- **Write here:** durable notes, briefs, ADRs, runbooks Boss should read in Obsidian.
- **Do not write:** secrets, API keys, raw credentials.
- **workspace notes/** = scratch/session; promote finished work into Obsidian.
- **Postgres** = structured truth (emails, CRM, deals); link IDs in notes, do not duplicate tables.
- Never write into another agent's Obsidian folder.

## Subfolders (create as needed)

- \`Briefs/\`, \`Runbooks/\`, \`Decisions/\`
- Admin also: \`Reports/\` (synced daily), \`Inbox/\` (Gmail triage summaries)
EOF
  chown 1000:1000 "$BASE/workspace-${agent}/OBSIDIAN.md" 2>/dev/null || true
}

patch_boot() {
  local agent=$1
  local f="$BASE/workspace-${agent}/BOOT.md"
  [[ -f "$f" ]] || return 0
  if ! grep -q OBSIDIAN.md "$f"; then
    sed -i 's/DATABASE.md/DATABASE.md, OBSIDIAN.md/' "$f" 2>/dev/null || true
  fi
}

cat > "$OBS/README.md" <<'EOF'
# Clawsum Obsidian vault

Single vault on the VPS: `/docker/clawsum/obsidian` (mounted at `/home/node/obsidian` in OpenClaw).

## Folder map

| Folder | Agent | Use |
|--------|-------|-----|
| Admin/ | admin | Ops, reports, inbox triage |
| Coding/ | coding | PRs, infra, deploy notes |
| Data/ | data | ETL, scrapers, pipelines |
| RealEstate/ | realestate | Deals, comps, markets |
| GHL/ | ghl | CRM, automations |
| Comms/ | comms | Templates, messaging |
| Research/ | research | Briefs, sources |
| Planning/ | planning | Roadmaps, ADRs |
| Paperclip/ | paperclip | Orchestration notes |
| _templates/ | — | Note templates |

## What syncs automatically

- **7:02 AM Chicago:** latest `global-YYYY-MM-DD.md` → `Admin/Reports/`

## Boss desktop

Sync this folder via **git**, **Syncthing**, or **SSHFS** — see [OBSIDIAN-VAULT.md](../docs/OBSIDIAN-VAULT.md).
EOF

cat > "$OBS/_templates/daily-note.md" <<'EOF'
# {{date}} — {{agent}}

## Done

## Next

## Links
EOF

cat > "$OBS/_templates/research-brief.md" <<'EOF'
# Research brief — {{title}}

**Date:** {{date}}  
**Agent:** research

## Question

## Findings

## Sources

## Handoff
EOF

cat > "$OBS/_templates/adr.md" <<'EOF'
# ADR — {{title}}

**Status:** proposed | accepted | superseded  
**Date:** {{date}}

## Context

## Decision

## Consequences
EOF

for pair in \
  "admin:Admin:Ops liaison — reports, triage, cross-domain links (no domain DB ownership)" \
  "coding:Coding:Code, CI, infra-as-code for Clawsum stack" \
  "data:Data:ETL, scrapers, data pipelines, report builds" \
  "realestate:RealEstate:Deals, comps, RE market (realestate DB only)" \
  "ghl:GHL:GHL CRM (crm schema only)" \
  "comms:Comms:Messaging templates and comms drafts" \
  "research:Research:Research briefs and synthesis" \
  "planning:Planning:Roadmaps, priorities, ADRs" \
  "paperclip:Paperclip:Orchestration and task breakdown notes"; do
  IFS=: read -r agent folder scope <<< "$pair"
  mkdir -p "$OBS/$folder"
  cat > "$OBS/$folder/README.md" <<EOF
# ${folder}

Agent: **${agent}**  
Container path: \`/home/node/obsidian/${folder}/\`

${scope}
EOF
  write_obsidian_md "$agent" "$folder" "$scope"
  patch_boot "$agent"
done

chown -R 1000:1000 "$OBS" "$BASE"/workspace-*/OBSIDIAN.md 2>/dev/null || true
echo "Seeded Obsidian vault + workspace OBSIDIAN.md for all agents"
