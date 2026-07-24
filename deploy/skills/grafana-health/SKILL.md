---
name: grafana-health
description: Checks Grafana/Prometheus health and prepares CEO-readable uptime summaries. Use for server health, embed URLs, or incident triage.
agents: [admin, coding]
cells: [clawsum-platform, hardware-local-ai, vocalitic]
tier_autonomous: 0
credentials: [GRAFANA_*, CLAWSUM_GRAFANA_*]
approval_actions: []
---

# Grafana health

1. Confirm Grafana up; use kiosk embed URL in cockpit Health tab.
2. Summarize red panels only for Boss.
3. Do not change datasource passwords autonomously.
