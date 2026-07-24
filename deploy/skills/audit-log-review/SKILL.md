---
name: audit-log-review
description: Reviews ops.audit_logs and approval history for governed actions. Use for compliance spot-checks or incident reconstruction.
agents: [admin, paperclip]
cells: ["*"]
tier_autonomous: 0
credentials: [POSTGRES_*]
approval_actions: []
---

# Audit log review

```sql
SELECT created_at, actor_name, action, tool_name, risk_level, business_id
FROM ops.audit_logs
ORDER BY created_at DESC
LIMIT 50;
```

Summarize anomalies for Boss; do not exfiltrate payloads with secrets.
