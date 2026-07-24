---
name: minio-archive-store
description: Stores large ChatGPT exports and email attachments in MinIO with keys recorded in Postgres. Use when raw archives must not live only on local disk.
agents: [data, coding, admin]
cells: [clawsum-platform]
tier_autonomous: 1
credentials: [MINIO_*, POSTGRES_*]
approval_actions: []
---

# MinIO archive store

1. Upload object to cell/platform bucket.
2. Record URI on `ops.chatgpt_imports.raw_archive_uri` or email attachment metadata.
3. Do not make buckets public.
4. Deletion of archives = Tier 2+.
