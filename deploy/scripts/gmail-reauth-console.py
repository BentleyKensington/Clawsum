#!/usr/bin/env python3
"""
Re-auth Gmail for clawsums@gmail.com (console / paste-code flow).

Run on VPS:
  python3 /docker/clawsum/scripts/gmail-reauth-console.py

1) Opens nothing — prints an auth URL
2) You open the URL, sign in as clawsums@gmail.com, allow access
3) Paste the verification code back into the terminal
4) Script updates GMAIL_REFRESH_TOKEN in /docker/clawsum/.env
5) Optionally rewires gog (--gog)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
SECRET_OUT = Path("/tmp/clawsum-gmail-client-secret.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
ADMIN = "clawsums@gmail.com"


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
    data = {
        "installed": {
            "client_id": cid,
            "client_secret": secret,
            "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    SECRET_OUT.write_text(json.dumps(data, indent=2) + "\n")
    os.chmod(SECRET_OUT, 0o600)
    return SECRET_OUT


def run_oauth(secret_path: Path) -> str:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)
    # Console-style: print URL, paste code (works over SSH)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    print("\n=== Gmail re-auth ===")
    print(f"1) Open this URL in a browser (incognito recommended)")
    print(f"2) Sign in ONLY as {ADMIN}")
    print("3) Approve access")
    print("4) Copy the code / paste below\n")
    print(auth_url)
    print()
    code = input("Paste authorization code here: ").strip()
    if not code:
        raise SystemExit("No code provided")
    flow.fetch_token(code=code)
    creds = flow.credentials
    if not creds.refresh_token:
        raise SystemExit(
            "No refresh_token returned. Revoke prior access at "
            "https://myaccount.google.com/permissions then retry with prompt=consent."
        )

    # Verify mailbox
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
    print(f"\nVerified mailbox: {email}")
    if email.lower() != ADMIN.lower():
        raise SystemExit(f"Signed in as {email}, expected {ADMIN}")
    return creds.refresh_token


def rewire_gog() -> None:
    script = ROOT / "scripts" / "install-gog-gmail-openclaw.sh"
    if not script.exists():
        print("install-gog-gmail-openclaw.sh missing — skip gog", file=sys.stderr)
        return
    # Reset corrupted file keyring for gog
    gog_home = ROOT / "data" / ".openclaw" / "gog"
    keyring = gog_home / "data" / "keyring"
    if keyring.exists():
        print(f"Clearing gog keyring at {keyring}")
        for p in keyring.glob("_gogcli_key_v1_*"):
            try:
                p.unlink()
            except OSError as e:
                print(f"  warn: {p}: {e}")
    env = os.environ.copy()
    # Ensure password exists
    cur = load_env(ENV_FILE)
    if not cur.get("GOG_KEYRING_PASSWORD"):
        import secrets

        pw = secrets.token_urlsafe(24)
        upsert_env(
            ENV_FILE,
            {
                "GOG_KEYRING_BACKEND": "file",
                "GOG_KEYRING_PASSWORD": pw,
            },
        )
        print("Generated new GOG_KEYRING_PASSWORD")
    elif "GOG_KEYRING_BACKEND" not in cur:
        upsert_env(ENV_FILE, {"GOG_KEYRING_BACKEND": "file"})

    print("Running install-gog-gmail-openclaw.sh …")
    subprocess.run(["bash", str(script)], check=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gog", action="store_true", help="Also reset/rewire OpenClaw gog")
    ap.add_argument(
        "--code",
        help="Authorization code (non-interactive). If omitted, prompts.",
    )
    ap.add_argument(
        "--print-url-only",
        action="store_true",
        help="Only print auth URL (for agent to show Boss), write state to /tmp",
    )
    args = ap.parse_args()

    env = load_env(ENV_FILE)
    secret_path = write_client_secret(env)

    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )

    if args.print_url_only:
        state_path = Path("/tmp/clawsum-gmail-oauth-state.json")
        # Persist flow client config; code exchange will recreate flow
        state_path.write_text(
            json.dumps({"auth_url": auth_url, "state": state, "secret": str(secret_path)})
            + "\n"
        )
        print(auth_url)
        return 0

    print("\n=== Gmail re-auth ===")
    print(f"Sign in ONLY as {ADMIN}")
    print(auth_url)
    print()
    code = (args.code or "").strip() or input("Paste authorization code here: ").strip()
    if not code:
        print("No code provided", file=sys.stderr)
        return 1

    # Google sometimes returns a URL-encoded code or full redirect URL
    if "code=" in code:
        m = re.search(r"[?&]code=([^&]+)", code)
        if m:
            code = m.group(1)

    flow.fetch_token(code=code)
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

    # Smoke: list 1 message
    res = svc.users().messages().list(userId="me", maxResults=1).execute()
    print(f"Gmail API OK — messages visible: {bool(res.get('messages'))}")

    if args.gog:
        rewire_gog()

    print("\nDone. Next:")
    print("  python3 /docker/clawsum/scripts/gmail-sync.py")
    print("  python3 /docker/clawsum/scripts/gmail-fetch-logo-attachment.py /tmp/clawsum-logo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
