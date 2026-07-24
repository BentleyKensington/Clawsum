# Gmail for Admin — monitor, archive, process

Dedicated inbox for Clawsum admin: **`clawsums@gmail.com`**. You can **forward** any mail to it; the stack **archives to Postgres** and the **7am report** summarizes inbox + Paperclip tasks.

---

## Architecture

```text
Your mail ──forward──► clawsums@gmail.com
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            gmail-sync.py (cron)   OpenClaw Gmail watcher (optional)
            ops.emails in Postgres   Real-time → admin agent → Telegram
                    │
                    ▼
            daily-global-report.py (7am)
            → CS Ops / your DM
```

| Layer | Role |
|-------|------|
| **Postgres `ops.emails`** | System of record — every message archived, triage status, domain guess |
| **`gmail-sync.py`** | Pull mail via Gmail API (backfill + every 15 min) |
| **Admin agent** | Triage, create Paperclip tasks, reply (via OpenClaw when Gmail watcher enabled) |
| **7am cron** | Platform health + **pending tasks** + **email backlog** + activity |

---

## Step 1 — Create the Gmail mailbox

1. Create a Google account for ops (or use a Workspace user).
2. Enable 2FA.
3. In Google Account → **Forwarding**, you can forward *from* other accounts **to** this address, or set rules in those accounts: “Forward to clawsums@gmail.com”.

---

## Step 2 — Google Cloud OAuth (read-only)

1. Open [Google Cloud Console](https://console.cloud.google.com/) → project **Clawsum** (create if needed).
2. **APIs & Services → Library** → enable **Gmail API**.
3. **OAuth consent screen** (Google may label this **Google Auth Platform**)

   **Important for `@gmail.com`:** choose **External** user type — **not Internal**.  
   Internal only works for users inside a **Google Workspace** org; a normal Gmail account will not work with Internal.

   - App name: Clawsum Admin  
   - User support email: your email  
   - Scopes: add `https://www.googleapis.com/auth/gmail.readonly` (under **User data**)

   **Test users** — only shown while the app is in **Testing** (not Production):

   | Where to look (2025/2026 UI) |
   |-----------------------------|
   | **APIs & Services → OAuth consent screen** → section **Test users** → **+ ADD USERS** |
   | Or **Google Auth Platform → Audience** → **Test users** → Add **`clawsums@gmail.com`** |

   If you **do not see** “Test users”:

   | Situation | What it means |
   |-----------|----------------|
   | Publishing status = **In production** | No test-user list — any Google account can try to sign in; `gmail.readonly` may still require [app verification](https://support.google.com/cloud/answer/9110914) for non-test users. |
   | User type = **Internal** | Wrong for `clawsums@gmail.com` — switch to **External** (new project if needed). |
   | Consent screen not finished | Complete all required steps (app name, email, scopes) and save; **Test users** appears after. |

   **If there is no Test users section:** you can still run `gmail-oauth-setup.py` — sign in as **clawsums@gmail.com**. If Google blocks with “app not verified”, add yourself under Test users (switch app back to **Testing** under **Audience → Publishing status**) or complete verification.

4. **Credentials → Create credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Download JSON → save as `client_secret.json` on your PC
5. On your **Windows PC** (browser opens once):

```powershell
cd c:\Projects\Clawsum\deploy\scripts
pip install google-auth-oauthlib google-auth google-api-python-client
python gmail-oauth-setup.py C:\path\to\client_secret.json
```

The script prints `GMAIL_*` lines — copy them to the VPS `.env`.

6. Add to `/docker/clawsum/.env`:

```env
GMAIL_ADMIN_ADDRESS=clawsums@gmail.com
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
GMAIL_BACKFILL_MAX=2000
GMAIL_SYNC_QUERY=in:all
```

---

## Step 3 — Database schema

On first deploy or migration:

```bash
docker exec -i clawsum-postgres-1 psql -U clawsum -d clawsum < /docker/clawsum/postgres-init/05-ops-email.sql
```

---

## Step 4 — Install Python deps on VPS

```bash
# Ubuntu VPS: install pip first if missing
sudo apt-get update && sudo apt-get install -y python3-pip
pip3 install --break-system-packages google-auth google-auth-oauthlib google-api-python-client psycopg2-binary
```

---

## Step 5 — Backfill historical mail

```bash
python3 /docker/clawsum/scripts/gmail-sync.py --backfill
```

Uses `GMAIL_SYNC_QUERY` (default `in:all`). Increase `GMAIL_BACKFILL_MAX` for more history.

---

## Step 6 — Cron: sync + review every 15 minutes

```bash
bash /docker/clawsum/scripts/install-gmail-inbox-review-cron.sh
# installs run-gmail-inbox-pipeline.sh (gmail-sync.py + gmail-inbox-review.py)
```

Legacy sync-only:

```bash
bash /docker/clawsum/scripts/install-gmail-sync-cron.sh
```

Prefer the **inbox review** cron so Hermes always has per-email analysis in `ops.email_reviews`.
---

## Step 7 — OpenClaw Control UI “Gmail connection” (gog skill)

The **dashboard “no Gmail connection”** message is **not** the same as `gmail-sync.py`.

| Path | What it does | Where configured |
|------|----------------|------------------|
| **`gmail-sync.py` + cron** | Archives mail → Postgres `ops.emails`, 7am report | `/docker/clawsum/.env` `GMAIL_*` |
| **OpenClaw `gog` skill** | Agents + Control UI use Gmail API via `gog` CLI | `GOG_HOME` under `.openclaw/gog` |

Your Google OAuth in `.env` can feed **both**. After OAuth (Steps 2–6), wire gog on the VPS:

```bash
bash /docker/clawsum/scripts/install-gog-gmail-openclaw.sh
python3 /docker/clawsum/scripts/enable-gog-skill.py
cd /docker/clawsum && docker compose up -d openclaw-gateway
```

Add to `.env` (if missing):

```env
GOG_KEYRING_BACKEND=file
GOG_KEYRING_PASSWORD=choose-a-long-random-secret
```

Verify inside the gateway container:

```bash
docker exec clawsum-openclaw-gateway-1 gog auth list
docker exec clawsum-openclaw-gateway-1 node dist/index.js skills check | grep gog
```

Refresh the Control UI — Gmail should show **connected** for `clawsums@gmail.com`.

---

## Step 8 (optional) — OpenClaw real-time Gmail watcher

For **instant** agent processing (not only cron), OpenClaw supports **Gmail Pub/Sub** via `gog` + hooks:

```bash
# Inside openclaw-cli container (requires gcloud, gog, public HTTPS — e.g. Tailscale funnel)
openclaw webhooks gmail setup --account clawsums@gmail.com
```

Configure delivery to Telegram admin in `openclaw.json`:

```json
"hooks": {
  "enabled": true,
  "gmail": {
    "account": "clawsums@gmail.com",
    "model": "openai/gpt-5.4",
    "deliver": {
      "channel": "telegram",
      "to": "<admin_chat_or_group>"
    }
  }
}
```

This path is more setup; **cron + DB** works without a public webhook.

---

## Admin processing workflow

| Step | Who | Action |
|------|-----|--------|
| 1 | Gmail | Mail arrives at **clawsums@gmail.com** (direct or forward) |
| 2 | Cron | `gmail-sync.py` → `ops.emails` |
| 3 | Review | `gmail-inbox-review.py` → cell + person + `ops.tasks` + questions |
| 4 | Triage | `gmail-triage.py` → Paperclip issues when action required |
| 5 | Hermes | Ask Boss; link reminders; drive outcomes |
| 6 | Domain agents | Work in Telegram / Boss UI after approval |

**Full inbox review:**

```bash
python3 /docker/clawsum/scripts/gmail-inbox-review.py --inbox-only --sync-first --markdown --create-reminders
# or:
bash /docker/clawsum/scripts/run-overwatch-crm.sh --review-inbox --sync-first
```

See [OVERWATCH-CRM.md](./OVERWATCH-CRM.md) for people / places / cells.

**SQL triage examples:**

```sql
-- Pending inbox count
SELECT COUNT(*) FROM ops.emails WHERE processing_status = 'pending';

-- Mark archived
UPDATE ops.emails SET processing_status = 'archived' WHERE gmail_id = '...';
```

Ask admin in Telegram: *“Triage pending Gmail: list subjects and suggest Paperclip tasks.”*

---

## 7am report (already includes)

After Gmail sync is running, the daily report adds:

- Email: received last 24h, pending triage, action_required
- Paperclip: open / in-progress / blocked tasks with titles
- Recent Paperclip activity (last 24h)

Override delivery: `TELEGRAM_REPORT_CHAT_ID` in `.env`.

---

## Troubleshooting: `403 access_denied` / “has not completed the Google verification process”

Google shows this when the OAuth app is in **Testing** and the account you sign in with is **not** on the **Test users** list (or you are not a project owner/editor).

**Fix (recommended):**

1. Open [Google Cloud Console](https://console.cloud.google.com/) → select the **same project** where you created the Desktop OAuth client.
2. Go to **APIs & Services → OAuth consent screen** (or **Google Auth Platform → Audience**).
3. Confirm **Publishing status** = **Testing** (not Production).
4. Find **Test users** → **+ ADD USERS** → enter exactly **`clawsums@gmail.com`** → Save.
5. Wait 1–2 minutes. In a private/incognito window (or sign out of other Google accounts), run `gmail-oauth-setup.py` again and sign in **only** as `clawsums@gmail.com`.

**Still blocked?**

| Check | Action |
|-------|--------|
| Wrong Google account in browser | Use incognito; pick `clawsums@gmail.com` at login. |
| Test user typo | Must match the mailbox exactly (no spaces). |
| Wrong Cloud project | Credentials JSON must be from the project where you added the test user. |
| User type **Internal** | Switch to **External** (Internal does not work for `@gmail.com`). |
| You are not a project member | Project **Owner** must add you, or sign in as the owner when running OAuth once. |

**Do not** switch to **In production** to skip test users unless you are ready for [Google app verification](https://support.google.com/cloud/answer/9110914) for `gmail.readonly` — that can take days and is not needed for a personal admin inbox while Testing + test user works.

---

## Security

- OAuth scope is **readonly** for sync script.
- Do not commit `.env` or `client_secret.json`.
- Admin agent should **ask Boss** before sending external email (see `ESCALATION.md`).
- For send capability later: separate OAuth scope + comms/admin policy.
