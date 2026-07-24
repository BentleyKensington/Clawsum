#!/usr/bin/env python3
"""
Gmail OAuth health + Boss Telegram alerts.

Why: clawsums@gmail.com sync/review must not fail silently (invalid_grant / missing env).

Usage:
  python3 gmail-oauth-health.py              # check; alert if broken (cooldown)
  python3 gmail-oauth-health.py --force      # alert even inside cooldown
  python3 gmail-oauth-health.py --dry-run    # print what would send
  python3 gmail-oauth-health.py --from-failure "gmail-sync: invalid_grant"

Also imported by gmail-sync.py on auth failure.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
STATE_FILE = ROOT / "data" / "reports" / "gmail-oauth-health.json"
DEFAULT_COOLDOWN_H = 6


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        out.setdefault(k, v)
    return out


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(STATE_FILE, 0o600)
    except OSError:
        pass


def telegram_chat_id(env: dict[str, str]) -> str:
    for key in (
        "TELEGRAM_ADMIN_CHAT_ID",
        "TELEGRAM_REPORT_CHAT_ID",
        "TELEGRAM_PAPERCLIP_GROUP_ID",
    ):
        v = (env.get(key) or "").strip()
        if v:
            return v
    # Fallback: OpenClaw admin group binding (common on this VPS)
    for path in (
        Path("/docker/clawsum/data/.openclaw/openclaw.json"),
        ROOT / "data" / ".openclaw" / "openclaw.json",
    ):
        if not path.exists():
            continue
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for b in cfg.get("bindings") or []:
            if b.get("agentId") != "admin":
                continue
            peer = (b.get("match") or {}).get("peer") or b.get("peer") or {}
            if peer.get("kind") == "group" and peer.get("id"):
                return str(peer["id"])
        # Prefer paperclip group if admin not bound
        for b in cfg.get("bindings") or []:
            if b.get("agentId") != "paperclip":
                continue
            peer = (b.get("match") or {}).get("peer") or b.get("peer") or {}
            if peer.get("kind") == "group" and peer.get("id"):
                return str(peer["id"])
    return ""


def send_telegram(text: str, token: str, chat_id: str) -> None:
    for i in range(0, len(text), 3900):
        chunk = text[i : i + 3900]
        payload = json.dumps({"chat_id": chat_id, "text": chunk}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            if not result.get("ok"):
                raise RuntimeError(f"telegram send failed: {result}")


def probe_oauth(env: dict[str, str]) -> tuple[bool, str]:
    """Return (ok, detail). Never includes secrets."""
    missing = [
        k
        for k in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN")
        if not env.get(k)
    ]
    if missing:
        return False, f"missing env: {', '.join(missing)}"

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as e:
        return False, f"google libs missing: {e}"

    try:
        creds = Credentials(
            token=None,
            refresh_token=env["GMAIL_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=env["GMAIL_CLIENT_ID"],
            client_secret=env["GMAIL_CLIENT_SECRET"],
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )
        creds.refresh(Request())
        svc = build("gmail", "v1", credentials=creds, cache_discovery=False)
        profile = svc.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress") or "?"
        expected = (env.get("GMAIL_ADMIN_ADDRESS") or "clawsums@gmail.com").lower()
        if email.lower() != expected:
            return False, f"signed in as {email}, expected {expected}"
        return True, f"ok mailbox={email}"
    except Exception as e:  # noqa: BLE001 — surface any auth failure
        name = type(e).__name__
        msg = str(e)
        # Truncate / scrub
        if "invalid_grant" in msg.lower() or name == "RefreshError":
            return False, "OAuth refresh failed (invalid_grant) — re-auth required"
        return False, f"{name}: {msg[:240]}"


def hours_since(iso: str | None) -> float:
    if not iso:
        return 1e9
    try:
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - then.astimezone(timezone.utc)).total_seconds() / 3600.0
    except ValueError:
        return 1e9


def failure_message(detail: str, mailbox: str, context: str | None) -> str:
    ctx = f"\nContext: {context}" if context else ""
    return (
        f"🚨 Clawsum Gmail OAuth BROKEN\n"
        f"Mailbox: {mailbox}\n"
        f"Issue: {detail}{ctx}\n"
        f"\n"
        f"Hermes inbox sync/review is offline until this is fixed.\n"
        f"\n"
        f"Fix (Boss PC):\n"
        f"1) python deploy/scripts/gmail-oauth-setup.py path/to/client_secret.json\n"
        f"   (sign in as {mailbox})\n"
        f"2) Paste new GMAIL_REFRESH_TOKEN into /docker/clawsum/.env\n"
        f"3) bash /docker/clawsum/scripts/install-gog-gmail-openclaw.sh\n"
        f"4) bash /docker/clawsum/scripts/run-gmail-inbox-pipeline.sh\n"
        f"\n"
        f"Or on VPS after browser auth code:\n"
        f"  python3 /docker/clawsum/scripts/gmail-reauth-console.py --gog\n"
    )


def recovery_message(mailbox: str, detail: str) -> str:
    return (
        f"✅ Clawsum Gmail OAuth restored\n"
        f"Mailbox: {mailbox}\n"
        f"Status: {detail}\n"
        f"Inbox sync/review pipeline can run again."
    )


def alert_boss(
    env: dict[str, str],
    text: str,
    *,
    dry_run: bool = False,
) -> bool:
    token = (env.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat = telegram_chat_id(env)
    if dry_run:
        print("--- telegram dry-run ---")
        print(f"chat={chat or '(missing)'}")
        print(text)
        return bool(token and chat)
    if not token or not chat:
        print(
            "WARN: cannot alert Boss — TELEGRAM_BOT_TOKEN or "
            "TELEGRAM_ADMIN_CHAT_ID/TELEGRAM_REPORT_CHAT_ID missing",
            file=sys.stderr,
        )
        return False
    try:
        send_telegram(text, token, chat)
        return True
    except (urllib.error.URLError, TimeoutError, RuntimeError) as e:
        print(f"WARN: telegram alert failed: {e}", file=sys.stderr)
        return False


def handle_result(
    ok: bool,
    detail: str,
    env: dict[str, str],
    *,
    force: bool = False,
    dry_run: bool = False,
    context: str | None = None,
) -> int:
    mailbox = env.get("GMAIL_ADMIN_ADDRESS", "clawsums@gmail.com")
    cooldown = float(env.get("GMAIL_OAUTH_ALERT_COOLDOWN_HOURS", str(DEFAULT_COOLDOWN_H)))
    state = load_state()
    was_failing = bool(state.get("failing"))

    if ok:
        state["last_ok_at"] = now_iso()
        state["last_error"] = None
        if was_failing:
            msg = recovery_message(mailbox, detail)
            sent = alert_boss(env, msg, dry_run=dry_run)
            state["last_recovery_alert_at"] = now_iso()
            state["failing"] = False
            state["alerted_while_failing"] = False
            save_state(state)
            print(detail)
            print("recovery alert sent" if sent else "recovery alert not sent")
            return 0
        state["failing"] = False
        save_state(state)
        print(detail)
        return 0

    # Failure path
    state["failing"] = True
    state["last_fail_at"] = now_iso()
    state["last_error"] = detail
    last_alert = state.get("last_alert_at")
    should_alert = force or (hours_since(last_alert) >= cooldown)

    if should_alert:
        msg = failure_message(detail, mailbox, context)
        sent = alert_boss(env, msg, dry_run=dry_run)
        if sent or dry_run:
            state["last_alert_at"] = now_iso()
            state["alerted_while_failing"] = True
        save_state(state)
        print(f"FAIL: {detail}", file=sys.stderr)
        print("Boss alert sent" if sent else "Boss alert NOT sent", file=sys.stderr)
        return 2

    save_state(state)
    print(
        f"FAIL: {detail} (alert suppressed; last alert {last_alert}, "
        f"cooldown={cooldown}h)",
        file=sys.stderr,
    )
    return 2


def notify_auth_failure(error: BaseException | str, context: str = "gmail-sync") -> None:
    """Call from other scripts on OAuth failure (best-effort)."""
    env = load_env()
    detail = str(error)
    if "invalid_grant" in detail.lower() or type(error).__name__ == "RefreshError":
        detail = "OAuth refresh failed (invalid_grant) — re-auth required"
    else:
        detail = f"{type(error).__name__ if not isinstance(error, str) else 'Error'}: {detail[:240]}"
    handle_result(False, detail, env, context=context)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="Alert even inside cooldown")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--from-failure",
        metavar="DETAIL",
        help="Record failure + alert without probing (pipeline hook)",
    )
    args = ap.parse_args()
    env = load_env()

    if args.from_failure:
        return handle_result(
            False,
            args.from_failure[:400],
            env,
            force=args.force,
            dry_run=args.dry_run,
            context="pipeline",
        )

    ok, detail = probe_oauth(env)
    return handle_result(
        ok, detail, env, force=args.force, dry_run=args.dry_run, context="health-check"
    )


if __name__ == "__main__":
    raise SystemExit(main())
