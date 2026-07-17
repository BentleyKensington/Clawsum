#!/bin/bash
set -euo pipefail
BASE=/docker/clawsum/data/.openclaw
PASS="${POSTGRES_PASSWORD:-clawsum_change_me}"

write_db() {
  local agent=$1 db=$2 schema=$3
  local dir="$BASE/workspace-${agent}"
  mkdir -p "$dir"
  cat > "$dir/DATABASE.md" <<EOF
# DATABASE.md — ${agent} agent

**Database:** \`${db}\` (isolated — do not use other agents' databases)
**Host:** \`postgres:5432\` (Docker network \`clawsum\`)
**User:** \`clawsum\`
**Primary schema:** \`${schema}\`

\`\`\`
postgresql://clawsum:***@postgres:5432/${db}
\`\`\`

## Crossover with other domains

- **realestate ↔ ghl:** Use Paperclip tasks or admin orchestration. No direct cross-DB queries.
- Shared read models (if approved by Boss) must be explicit API/export jobs run by the **data** agent.

EOF
  chown 1000:1000 "$dir/DATABASE.md" 2>/dev/null || true
}

write_db admin clawsum ops
write_db coding clawsum coding
write_db data clawsum data
write_db comms clawsum comms
write_db research clawsum research
write_db planning clawsum planning
write_db realestate realestate deals

write_db ghl ghl crm

echo "Seeded DATABASE.md for all agents."
