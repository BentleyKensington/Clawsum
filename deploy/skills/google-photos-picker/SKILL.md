---
name: google-photos-picker
description: Let Gerald pick photos from clawsums@gmail.com via Google Photos Picker API. No full-library sync.
agents: [printful, media, shopify, admin]
cells: [media-production, acceptai-fastbuy, clawsum-platform]
tier_autonomous: 1
credentials: [GMAIL_*, GOG_*, GOOGLE_PHOTOS_ACCOUNT]
approval_actions: []
---

# Google Photos Picker

See [GOOGLE-PHOTOS-ACCESS.md](../../docs/GOOGLE-PHOTOS-ACCESS.md).

## Instructions

1. If gog is installed:

```bash
gog photos picker create --max-items 20 --json
```

2. Send Gerald the `pickerUri` (Discord/Telegram). He must be signed into clawsums@gmail.com.
3. Poll until `mediaItemsSet`. Download via gog/helper; write MinIO; put object keys on the Paperclip issue.
4. Never try Photos Library full search (removed 2025).

Missing OAuth scope → Admin runs Gmail/Photos re-consent. Do not invent a service-account bypass.
