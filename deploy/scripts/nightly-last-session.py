#!/usr/bin/env python3
"""Rewrite LAST_SESSION.md from live ops data. No invented counts."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
HERMES = ROOT / "paperclip-data" / ".hermes"
EXAMPLE = ROOT / "examples" / "hermes-cockpit" / "LAST_SESSION.md"
TZ = ZoneInfo("America/Chicago")
PAPERCLIP_API = os.environ.get("PAPERCLIP_API", "http://127.0.0.1:3100/api")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        out.setdefault(k, v)
    return out


def http_json(url: str, timeout: int = 12):
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode(errors="replace"))
    except Exception as exc:
        return 0, {"error": str(exc)}


def psql(sql: str) -> str | None:
    env = load_env()
    try:
        out = subprocess.run(
            [
                "docker", "exec", "clawsum-postgres-1", "psql",
                "-U", env.get("POSTGRES_USER", "clawsum"),
                "-d", env.get("POSTGRES_DB", "clawsum"),
                "-t", "-A", "-c", sql,
            ],
            capture_output=True, text=True, timeout=20,
        )
        if out.returncode == 0:
            return (out.stdout or "").strip()
    except Exception:
        pass
    return None


def issues(env: dict, status: str) -> list[dict]:
    cid = (env.get("PAPERCLIP_COMPANY_ID") or "").strip()
    if not cid:
        return []
    code, data = http_json(f"{PAPERCLIP_API}/companies/{cid}/issues?status={status}")
    if code != 200 or not isinstance(data, list):
        return []
    return data


def fmt_issue(it: dict) -> str:
    ident = it.get("identifier") or it.get("id") or "?"
    title = (it.get("title") or "untitled").strip()[:80]
    return f"{ident}: {title}"


def gmail_health() -> str:
    path = ROOT / "data" / "reports" / "gmail-oauth-health.json"
    if not path.is_file():
        return "Gmail OAuth health file missing"
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "Gmail OAuth health unreadable"
    if d.get("failing"):
        return f"Gmail OAuth failing: {d.get('last_error') or 'unknown'}"
    return "Gmail OAuth ok"


def hermes_gateway() -> str:
    code, data = http_json("http://127.0.0.1:9119/api/status", timeout=5)
    if code != 200 or not isinstance(data, dict):
        return "Hermes dashboard status unavailable"
    if data.get("gateway_running"):
        return "Hermes gateway running"
    return f"Hermes gateway {data.get('gateway_state') or 'stopped'}"


def build(env: dict) -> str:
    now = datetime.now(TZ)
    stamp = now.strftime("%Y-%m-%d %H:%M %Z")
    todo = issues(env, "todo")
    prog = issues(env, "in_progress")
    blocked = issues(env, "blocked")
    inbox = psql(
        "SELECT COUNT(*) FROM ops.emails WHERE COALESCE(review_status,'') "
        "IN ('needs_boss','action_required')"
    )
    inbox_24h = psql(
        "SELECT COUNT(*) FROM ops.emails WHERE received_at > NOW() - INTERVAL '24 hours'"
    )
    approvals = psql(
        "SELECT COUNT(*) FROM ops.approvals WHERE status IN ('pending','open')"
    )

    done: list[str] = [f"Nightly handoff generated {stamp} from live counts (not invented)."]
    if inbox_24h is not None:
        done.append(f"Inbox last 24h: {inbox_24h} messages archived")
    done.append(gmail_health())
    done.append(hermes_gateway())
    if prog:
        done.append("In progress: " + "; ".join(fmt_issue(x) for x in prog[:5]))

    open_items: list[str] = []
    if inbox not in (None, "0"):
        open_items.append(f"Triage inbox needs_boss/action_required ({inbox})")
    if approvals not in (None, "0"):
        open_items.append(f"Decide pending approvals ({approvals})")
    for it in (prog + blocked + todo)[:8]:
        open_items.append(fmt_issue(it))
    if not open_items:
        open_items.append("No open Paperclip/inbox counts available — check APIs in the morning.")

    risks: list[str] = [
        "Heartbeats stay off until RESUME-POLICY / CLA-41",
        "Gmail Testing-mode tokens die every 7 days until the OAuth app is In production",
        "New 7:30 jobs must use run-at-chicago.sh (this VPS ignores CRON_TZ)",
    ]

    summary_bits = [
        f"Nightly wrap {now.strftime('%Y-%m-%d')}.",
        f"Paperclip in_progress={len(prog)} todo={len(todo)} blocked={len(blocked)}.",
    ]
    if inbox is not None:
        summary_bits.append(f"Inbox needs Boss={inbox}.")
    if approvals is not None:
        summary_bits.append(f"Pending approvals={approvals}.")
    summary_bits.append(gmail_health() + ". " + hermes_gateway() + ".")

    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {x}" for x in items if x)

    def numbered(items: list[str]) -> str:
        return "\n".join(f"{i}. {x}" for i, x in enumerate(items, 1) if x)

    return (
        "# LAST_SESSION.md — handoff\n\n"
        f"_Nightly cron rewrite {stamp}. Wrap session during the day still wins until the next night._\n\n"
        "## Summary\n\n"
        + " ".join(summary_bits)
        + "\n\n## Done recently\n\n"
        + bullets(done)
        + "\n\n## Open for next session\n\n"
        + numbered(open_items)
        + "\n\n## Risks\n\n"
        + bullets(risks)
        + "\n"
    )


def write(text: str) -> list[Path]:
    written: list[Path] = []
    HERMES.mkdir(parents=True, exist_ok=True)
    dests = [HERMES / "LAST_SESSION.md", EXAMPLE]
    for path in dests:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            written.append(path)
        except OSError as exc:
            print(f"WARN write {path}: {exc}", file=sys.stderr)
    briefs = HERMES / "session-briefs"
    briefs.mkdir(parents=True, exist_ok=True)
    night = briefs / (datetime.now(TZ).strftime("%Y-%m-%d-%H%M%S") + "-nightly.md")
    night.write_text(text, encoding="utf-8")
    written.append(night)
    return written


def main() -> int:
    env = load_env()
    text = build(env)
    if "--dry-run" in sys.argv:
        print(text)
        return 0
    for path in write(text):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
