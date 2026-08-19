# Google Photos for clawsums@gmail.com

**Policy:** Picker or local mirror only. Google **removed full-library scopes** (31 Mar 2025). Nothing in Clawsum will “sync the camera roll.”

Related: [MEDIA-PRODUCTION-STUDIO.md](./MEDIA-PRODUCTION-STUDIO.md) · OpenClaw gog photos-picker

---

## Who needs it

| Agent | Why |
|-------|-----|
| **Printful** | Mockups, merch photos Gerald already shot |
| **Media** | Stills / B-roll Gerald selects |
| **Shopify** | PDP images Gerald selects |
| **AcceptAI / Vocalitic** | Product screenshots if Gerald picks them |

---

## Setup (same Google Cloud project as Gmail)

1. Enable **Google Photos Picker API** (`photospicker.googleapis.com`).
2. OAuth client already used for `gmail.readonly` — add scope `https://www.googleapis.com/auth/photospicker.mediaitems.readonly`.
3. Re-consent as **clawsums@gmail.com** (test user if app is in Testing).
4. On VPS, if using gog:

```bash
gog auth add clawsums@gmail.com --services photospicker
gog photos picker create --max-items 20 --open --json
```

5. Gerald picks photos in Google’s UI. Agent polls session, downloads via helper (short-lived `baseUrl`). Store blobs in **MinIO**, not Discord.

Env (optional if gog keyring is enough):

```env
GOOGLE_PHOTOS_ACCOUNT=clawsums@gmail.com
# Prefer gog keyring; do not add extra client secrets to git
```

---

## Skill

`google-photos-picker` — Printful, Media, Shopify, Admin.

Tier 0: create session + tell Gerald the picker URL.  
Tier 1: after he picks, copy files to MinIO `clawsum-media` / merch prefix.  
Never attempt Library API full search.
