#!/usr/bin/env python3
"""
Re-auth Gmail for clawsums@gmail.com (SSH-friendly, no OOB).

Google deprecated urn:ietf:wg:oauth:2.0:oob — that caused:
  Error 400: invalid_request  (flowName=GeneralOAuthFlow)

New flow (Desktop OAuth client):
  1) Script prints an auth URL (redirect = http://127.0.0.1:8765/)
  2) You open it, sign in as clawsums@gmail.com, Allow
  3) Browser goes to 127.0.0.1 — page may fail to load; that is OK
  4) Copy the FULL address-bar URL (has ?code=...) and paste here
  5) Script exchanges code → writes GMAIL_REFRESH_TOKEN to .env

Run on VPS:
  python3 /docker/clawsum/scripts/gmail-reauth-console.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
SECRET_OUT = Path("/tmp/clawsum-gmail-client-secret.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
ADMIN = "clawsums@gmail.com"
# Loopback — required now that OOB is dead. Desktop clients allow this by default.
REDIRECT_URI = "http://127.0.0.1:8765/"


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, _, v = raw.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def upsert_env(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text().splitlines() if path.exists() else []
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in updates:
                out.append(f"{k}={updates[k]}")
                seen.add(k)
                continue
        out.append(line)
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")
    path.write_text("\n".join(out) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def write_client_secret(env: dict[str, str]) -> Path:
    cid = env.get("GMAIL_CLIENT_ID")
    secret = env.get("GMAIL_CLIENT_SECRET")
    if not cid or not secret:
        raise SystemExit("Missing GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET in .env")
    # Desktop ("installed") client — no OOB
    data = {
        "installed": {
            "client_id": cid,
            "client_secret": secret,
            "redirect_uris": [
                REDIRECT_URI,
                "http://localhost:8765/",
                "http://127.0.0.1:8765",
            ],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    SECRET_OUT.write_text(json.dumps(data, indent=2) + "\n")
    os.chmod(SECRET_OUT, 0o600)
    return SECRET_OUT


def extract_code(pasted: str) -> str:
    pasted = (pasted or "").strip().strip('"').strip("'")
    if not pasted:
        raise SystemExit("No code/URL provided")
    if pasted.startswith("http://") or pasted.startswith("https://"):
        qs = parse_qs(urlparse(pasted).query)
        if qs.get("error"):
            raise SystemExit(f"Google returned error in redirect: {qs['error']}")
        if not qs.get("code"):
            raise SystemExit("URL has no code= parameter — paste the full redirect URL")
        return qs["code"][0]
    if "code=" in pasted:
        m = re.search(r"[?&#]code=([^&]+)", pasted)
        if m:
            return m.group(1)
    # raw code
    return pasted


def rewire_gog() -> None:
    script = ROOT / "scripts" / "install-gog-gmail-openclaw.sh"
    if not script.exists():
        print("install-gog-gmail-openclaw.sh missing — skip gog", file=sys.stderr)
        return
    gog_home = ROOT / "data" / ".openclaw" / "gog"
    keyring = gog_home / "data" / "keyring"
    if keyring.exists():
        print(f"Clearing gog keyring at {keyring}")
        for p in keyring.glob("_gogcli_key_v1_*"):
            try:
                p.unlink()
            except OSError as e:
                print(f"  warn: {p}: {e}")
    cur = load_env(ENV_FILE)
    if not cur.get("GOG_KEYRING_PASSWORD"):
        import secrets

        pw = secrets.token_urlsafe(24)
        upsert_env(
            ENV_FILE,
            {"GOG_KEYRING_BACKEND": "file", "GOG_KEYRING_PASSWORD": pw},
        )
        print("Generated new GOG_KEYRING_PASSWORD")
    elif "GOG_KEYRING_BACKEND" not in cur:
        upsert_env(ENV_FILE, {"GOG_KEYRING_BACKEND": "file"})
    print("Running install-gog-gmail-openclaw.sh …")
    subprocess.run(["bash", str(script)], check=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gog", action="store_true", help="Also reset/rewire OpenClaw gog")
    ap.add_argument("--code", help="Auth code or full redirect URL (non-interactive)")
    ap.add_argument(
        "--print-url-only",
        action="store_true",
        help="Only print auth URL",
    )
    args = ap.parse_args()

    env = load_env(ENV_FILE)
    secret_path = write_client_secret(env)
    state_path = Path("/tmp/clawsum-gmail-oauth-state.json")

    from google_auth_oauthlib.flow import Flow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    # Resume a --print-url-only flow so PKCE code_verifier still matches.
    pending = {}
    if args.code and state_path.is_file() and not args.print_url_only:
        try:
            pending = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pending = {}

    # Use Flow (not InstalledAppFlow OOB path) with explicit loopback redirect
    flow = Flow.from_client_secrets_file(
        str(pending.get("secret") or secret_path),
        scopes=SCOPES,
        redirect_uri=pending.get("redirect_uri") or REDIRECT_URI,
        state=pending.get("state"),
    )
    if pending.get("code_verifier"):
        flow.code_verifier = pending["code_verifier"]

    if not pending:
        # Do NOT set include_granted_scopes — it often triggers invalid_request
        auth_url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )
    else:
        auth_url = pending.get("auth_url") or ""
        state = pending.get("state")

    if args.print_url_only:
        state_path.write_text(
            json.dumps(
                {
                    "auth_url": auth_url,
                    "state": state,
                    "secret": str(secret_path),
                    "redirect_uri": REDIRECT_URI,
                    "code_verifier": getattr(flow, "code_verifier", None),
                }
            )
            + "\n"
        )
        print(auth_url)
        return 0

    print("\n=== Gmail re-auth (loopback — OOB is dead) ===")
    print(f"Sign in ONLY as {ADMIN}")
    print(f"OAuth client must be type: Desktop app")
    print()
    print("1) Open this URL in an incognito window:")
    print(auth_url)
    print()
    print("2) Approve access.")
    print("3) Browser redirects to 127.0.0.1:8765 — page may say connection refused.")
    print("   That is EXPECTED when running over SSH.")
    print("4) Copy the ENTIRE address-bar URL (starts with http://127.0.0.1:8765/?code=...)")
    print("   and paste it below.\n")

    pasted = (args.code or "").strip() or input("Paste full redirect URL (or code): ").strip()
    code = extract_code(pasted)

    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        print(f"Token exchange failed: {exc}", file=sys.stderr)
        print(
            "\nHints:\n"
            "  - OAuth client must be Desktop app (not Web)\n"
            "  - Paste the FULL redirect URL, not just part of it\n"
            "  - Add clawsums@gmail.com as Test user if app is in Testing\n"
            "  - Revoke old access: https://myaccount.google.com/permissions\n",
            file=sys.stderr,
        )
        return 1

    creds = flow.credentials
    if not creds.refresh_token:
        print(
            "No refresh_token. Revoke Clawsum at https://myaccount.google.com/permissions and retry.",
            file=sys.stderr,
        )
        return 2

    c = Credentials(
        token=creds.token,
        refresh_token=creds.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds.client_id,
        client_secret=creds.client_secret,
        scopes=SCOPES,
    )
    if not c.valid:
        c.refresh(Request())
    svc = build("gmail", "v1", credentials=c, cache_discovery=False)
    profile = svc.users().getProfile(userId="me").execute()
    email = profile.get("emailAddress", "")
    print(f"Verified mailbox: {email}")
    if email.lower() != ADMIN.lower():
        print(f"ERROR: signed in as {email}, expected {ADMIN}", file=sys.stderr)
        return 3

    upsert_env(
        ENV_FILE,
        {
            "GMAIL_ADMIN_ADDRESS": ADMIN,
            "GMAIL_REFRESH_TOKEN": creds.refresh_token,
            "GMAIL_CLIENT_ID": env.get("GMAIL_CLIENT_ID", creds.client_id or ""),
            "GMAIL_CLIENT_SECRET": env.get(
                "GMAIL_CLIENT_SECRET", creds.client_secret or ""
            ),
        },
    )
    print(f"Updated {ENV_FILE} with new GMAIL_REFRESH_TOKEN")

    res = svc.users().messages().list(userId="me", maxResults=1).execute()
    print(f"Gmail API OK — messages visible: {bool(res.get('messages'))}")

    if args.gog:
        rewire_gog()

    print("\nDone. Next:")
    print("  python3 /docker/clawsum/scripts/gmail_oauth_health.py")
    print("  python3 /docker/clawsum/scripts/gmail-sync.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
