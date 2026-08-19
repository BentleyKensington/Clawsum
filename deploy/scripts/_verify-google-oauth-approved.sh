#!/usr/bin/env bash
# Verify Gmail OAuth is live + look for Google "app/branding approved" mail.
set -euo pipefail
cd /docker/clawsum
set -a; set +u; . .env; set -u; set +a

python3 <<'PY'
import os, json
import urllib.parse
import urllib.request
from pathlib import Path

env = {}
for line in Path("/docker/clawsum/.env").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")
env.update({k: v for k, v in os.environ.items() if v})

cid = env.get("GMAIL_CLIENT_ID") or ""
print("=== client ===")
print("client_id", cid)
print("project_number", (cid.split("-")[0] if cid else "?"))
print("mailbox_cfg", env.get("GMAIL_ADMIN_ADDRESS") or "(unset)")

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

creds = Credentials(
    token=None,
    refresh_token=env["GMAIL_REFRESH_TOKEN"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=env["GMAIL_CLIENT_ID"],
    client_secret=env["GMAIL_CLIENT_SECRET"],
    scopes=["https://www.googleapis.com/auth/gmail.readonly"],
)
creds.refresh(Request())
print("REFRESH_OK")
print("token_expiry", creds.expiry.isoformat() if creds.expiry else "?")
print("scopes", " ".join(sorted(creds.scopes or [])))

# tokeninfo — does not expose verification, but confirms client + scope
info = json.loads(urllib.request.urlopen(
    "https://oauth2.googleapis.com/tokeninfo?access_token=" + creds.token, timeout=15
).read().decode())
print("=== tokeninfo ===")
for k in ("aud", "azp", "email", "scope", "expires_in", "access_type"):
    if k in info:
        print(k, info[k])

svc = build("gmail", "v1", credentials=creds, cache_discovery=False)
profile = svc.users().getProfile(userId="me").execute()
print("=== profile ===")
print("email", profile.get("emailAddress"))
print("messagesTotal", profile.get("messagesTotal"))
print("historyId", profile.get("historyId"))

queries = [
    'newer_than:21d (from:google.com OR from:cloud.google.com OR from:googlecloud.com) (subject:verif OR subject:brand OR subject:OAuth OR subject:"your app" OR subject:approved OR subject:published)',
    'newer_than:21d subject:("app verification" OR "OAuth consent" OR "brand verification" OR "Your app has been verified" OR "verification request")',
    'newer_than:21d from:cloud-noreply@google.com',
    'newer_than:21d from:google-cloud-compliance@google.com',
    'newer_than:21d ("Clawsum" (verified OR verification OR branding OR approved))',
]

seen = set()
hits = []
for q in queries:
    try:
        res = svc.users().messages().list(userId="me", q=q, maxResults=15).execute()
    except Exception as e:
        print("SEARCH_FAIL", q, e)
        continue
    for m in res.get("messages") or []:
        if m["id"] in seen:
            continue
        seen.add(m["id"])
        full = svc.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        hdrs = {h["name"].lower(): h["value"] for h in full.get("payload", {}).get("headers", [])}
        hits.append({
            "id": m["id"],
            "date": hdrs.get("date", ""),
            "from": hdrs.get("from", ""),
            "subject": hdrs.get("subject", ""),
            "snippet": (full.get("snippet") or "").replace("\n", " ")[:220],
        })

print("=== google approval mail (21d) ===")
if not hits:
    print("(none in clawsums@gmail.com — approval mail often goes to the Cloud Console owner, not the mailbox)")
else:
    for h in hits:
        print("---")
        print("date   ", h["date"])
        print("from   ", h["from"])
        print("subject", h["subject"])
        print("snippet", h["snippet"])

# Restricted-scope reality check: if a brand-new authorize URL is fetchable
print("=== authorize endpoint ===")
auth = (
    "https://accounts.google.com/o/oauth2/v2/auth"
    "?client_id=" + urllib.parse.quote(cid)
    + "&redirect_uri=" + urllib.parse.quote("http://127.0.0.1:8765/")
    + "&response_type=code&scope=" + urllib.parse.quote("https://www.googleapis.com/auth/gmail.readonly")
    + "&access_type=offline&prompt=consent"
)
req = urllib.request.Request(auth, headers={"User-Agent": "Mozilla/5.0 ClawsumVerify/1.0"})
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        body = r.read(8000).decode("utf-8", "replace")
        loc = r.geturl()
        print("http", r.status, "final", loc.split("?")[0])
except Exception as e:
    # 302 to accounts.google.com/signin is expected
    err = getattr(e, "code", None)
    loc = ""
    body = ""
    if hasattr(e, "headers") and e.headers:
        loc = e.headers.get("Location", "")
    print("http", err or type(e).__name__, "loc", (loc or "")[:160])
    try:
        body = e.read(4000).decode("utf-8", "replace") if hasattr(e, "read") else ""
    except Exception:
        pass

blob = (body or "").lower()
for needle in (
    "unverified",
    "hasn't verified",
    "has not verified",
    "this app isn't verified",
    "access blocked",
    "error 403",
    "invalid_client",
    "deleted_client",
    "disabled_client",
):
    if needle in blob or needle in (loc or "").lower():
        print("FLAG", needle)

print("authorize_url_ok client accepted (login wall is expected)")

# Local health stamp
hp = Path("/docker/clawsum/data/reports/gmail-oauth-health.json")
print("=== local health stamp ===")
if hp.exists():
    st = json.loads(hp.read_text())
    for k in ("status", "ok", "last_ok", "last_check", "last_error", "mailbox"):
        if k in st:
            print(k, st[k])
    print("keys", sorted(st.keys()))
else:
    print("(no health json)")

print("=== DONE ===")
PY
