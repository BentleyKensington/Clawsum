#!/usr/bin/env python3
"""
Clawsum daily Boss brief — plain language, decision-focused.
Scheduled for 7:30am America/Chicago via run-daily-global-report.sh
(CRON_TZ is unreliable on this VPS; the wrapper gates Chicago time).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
REPORT_DIR = ROOT / "data" / "reports"
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


def http_get(url: str, timeout: int = 12) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode(errors="replace")[:8000]
    except Exception as e:
        return 0, str(e)


def _psql(sql: str) -> str | None:
    env = load_env()
    try:
        out = subprocess.run(
            [
                "docker",
                "exec",
                "clawsum-postgres-1",
                "psql",
                "-U",
                env.get("POSTGRES_USER", "clawsum"),
                "-d",
                env.get("POSTGRES_DB", "clawsum"),
                "-t",
                "-A",
                "-c",
                sql,
            ],
            capture_output=True,
            text=True,
            timeout=25,
        )
        if out.returncode == 0:
            return (out.stdout or "").strip()
    except Exception:
        pass
    return None


def _company_id(env: dict) -> str:
    return (env.get("PAPERCLIP_COMPANY_ID") or "").strip()


def fetch_issues(env: dict, status: str) -> list[dict]:
    cid = _company_id(env)
    if not cid:
        return []
    code, body = http_get(f"{PAPERCLIP_API}/companies/{cid}/issues?status={status}")
    if code != 200:
        return []
    try:
        data = json.loads(body)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def issue_title(issue: dict) -> str:
    t = (issue.get("title") or "Untitled").strip()
    return t[:90]


def platform_ok() -> tuple[bool, str]:
    """One plain sentence on whether the shop is open."""
    problems: list[str] = []
    try:
        out = subprocess.run(
            ["docker", "ps", "--filter", "name=clawsum", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        rows = [r for r in (out.stdout or "").splitlines() if r.strip()]
        critical = ("openclaw-gateway", "postgres", "paperclip")
        for name in critical:
            hit = next((r for r in rows if name in r), None)
            if not hit:
                problems.append(f"{name} is not running")
            elif "(unhealthy)" in hit.lower() or "Restarting" in hit:
                problems.append(f"{name} looks unhealthy")
    except Exception:
        problems.append("could not check running services")

    gw = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:48166") + "/healthz"
    code, _ = http_get(gw, timeout=5)
    if code != 200:
        problems.append("the chat gateway is not answering")

    if problems:
        return False, "Something needs attention: " + "; ".join(problems[:3]) + "."
    return True, "Core systems are up and running."


def inbox_bits() -> tuple[list[str], list[str]]:
    """Return (highlights, needs_you)."""
    highlights: list[str] = []
    needs: list[str] = []
    if not _psql("SELECT to_regclass('ops.emails')"):
        return highlights, needs

    last24 = _psql(
        "SELECT COUNT(*) FROM ops.emails WHERE received_at > NOW() - INTERVAL '24 hours'"
    )
    needs_boss = _psql(
        "SELECT COUNT(*) FROM ops.email_reviews WHERE needs_boss IS TRUE "
        "AND analyzed_at > NOW() - INTERVAL '7 days'"
    )
    # Prefer recent needs_boss subjects
    pending_rows = _psql(
        """
        SELECT COALESCE(
          NULLIF(e.analysis_summary, ''),
          NULLIF(r.summary, ''),
          e.subject,
          '(no subject)'
        )
        FROM ops.email_reviews r
        JOIN ops.emails e ON e.id = r.email_id
        WHERE r.needs_boss IS TRUE OR e.review_status = 'needs_boss'
        ORDER BY COALESCE(r.analyzed_at, e.received_at) DESC NULLS LAST
        LIMIT 5
        """
    )
    if last24 and last24 != "0":
        highlights.append(f"{last24} new email(s) hit the archive in the last day.")
    elif last24 == "0":
        highlights.append("No new archived email in the last day.")

    if needs_boss and int(needs_boss or 0) > 0:
        needs.append(f"{needs_boss} inbox item(s) still need your call.")
        if pending_rows:
            for row in pending_rows.splitlines()[:4]:
                needs.append(f"• {row[:80]}")
    return highlights, needs


def reminder_bits() -> list[str]:
    lines: list[str] = []
    if not _psql("SELECT to_regclass('ops.reminders')"):
        return lines
    overdue = _psql(
        "SELECT COUNT(*) FROM ops.reminders WHERE completed_at IS NULL "
        "AND due_date < CURRENT_DATE AND (snoozed_until IS NULL OR snoozed_until < CURRENT_DATE)"
    )
    sample = _psql(
        "SELECT title FROM ops.reminders WHERE completed_at IS NULL "
        "AND due_date < CURRENT_DATE AND (snoozed_until IS NULL OR snoozed_until < CURRENT_DATE) "
        "ORDER BY due_date NULLS LAST LIMIT 3"
    )
    n = int(overdue or 0)
    if n <= 0:
        return lines
    if n >= 20:
        lines.append(
            f"There’s a large overdue follow-up backlog ({n}). Oldest few — rest can wait for a cleanup pass:"
        )
    else:
        lines.append(f"{n} reminder(s) are past due:")
    if sample:
        for row in sample.splitlines()[:3]:
            lines.append(f"• {row[:80]}")
    return lines


def task_bits(env: dict) -> tuple[list[str], list[str], list[str]]:
    """blocked / in_progress / todo highlights in plain English."""
    blocked = fetch_issues(env, "blocked")
    in_prog = fetch_issues(env, "in_progress")
    todo = fetch_issues(env, "todo") + fetch_issues(env, "backlog")

    need_you: list[str] = []
    moving: list[str] = []
    waiting: list[str] = []

    if blocked:
        need_you.append(f"{len(blocked)} task(s) are blocked and waiting on a decision or unblock.")
        for i in blocked[:4]:
            need_you.append(f"• {issue_title(i)}")
    if in_prog:
        moving.append(f"{len(in_prog)} task(s) are actively in progress.")
        for i in in_prog[:3]:
            moving.append(f"• {issue_title(i)}")
    if todo:
        waiting.append(f"{len(todo)} task(s) are queued and not started yet.")
        for i in todo[:3]:
            waiting.append(f"• {issue_title(i)}")
    return need_you, moving, waiting


def archive_bits() -> list[str]:
    # Skip archive clutter in the morning brief — Jarvis can surface it on request.
    return []


def agent_review_bits() -> tuple[list[str], list[str]]:
    """Load per-agent morning paragraphs + Hermes leverage alerts."""
    path = REPORT_DIR / "agent-daily-briefs.json"
    if not path.exists():
        try:
            subprocess.run(
                ["/usr/bin/python3", str(ROOT / "scripts" / "daily-agent-review.py")],
                timeout=45,
                check=False,
            )
        except Exception:
            pass
    if not path.exists():
        return [], []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return [], []
    alerts = [str(a) for a in (data.get("hermes_alerts") or []) if a]
    lines: list[str] = []
    for row in data.get("briefs") or []:
        if not isinstance(row, dict):
            continue
        summary = (row.get("summary") or "").strip()
        if summary:
            lines.append(f"• {summary[:160]}")
    return alerts, lines[:12]


def build_brief(env: dict) -> str:
    now = datetime.now(TZ)
    ok, health = platform_ok()
    inbox_h, inbox_need = inbox_bits()
    rem = reminder_bits()
    need_you, moving, waiting = task_bits(env)
    archive = archive_bits()
    hermes_alerts, agent_lines = agent_review_bits()

    # Merge "needs you" buckets
    decisions: list[str] = []
    decisions.extend(inbox_need)
    decisions.extend(need_you)
    decisions.extend(rem)
    decisions.extend(archive)

    parts: list[str] = [
        "Good morning, Boss.",
        f"Here’s your Clawsum brief for {now.strftime('%A, %B %-d')} ({now.strftime('%-I:%M %p %Z')}).",
        "",
        health if ok else f"Heads up — {health}",
        "",
    ]

    if decisions:
        parts.append("What needs you")
        parts.append("────────────────")
        parts.extend(decisions[:12])
        parts.append("")
    else:
        parts.append("Nothing urgent is waiting on your decision right now.")
        parts.append("")

    if moving:
        parts.append("Moving today")
        parts.append("────────────────")
        parts.extend(moving[:8])
        parts.append("")

    if waiting and not decisions:
        parts.append("On deck")
        parts.append("────────────────")
        parts.extend(waiting[:6])
        parts.append("")
    elif waiting:
        # Keep short when decisions already dominate
        parts.append(f"Also queued: {waiting[0]}")
        parts.append("")

    if inbox_h:
        parts.append("Inbox pulse")
        parts.append("────────────────")
        parts.extend(inbox_h[:3])
        parts.append("")

    if hermes_alerts:
        parts.append("Hermes alerts — what moves the needle")
        parts.append("────────────────")
        parts.extend(f"• {a}" for a in hermes_alerts[:6])
        parts.append("")

    if agent_lines:
        parts.append("Team overnight reviews")
        parts.append("────────────────")
        parts.extend(agent_lines[:10])
        parts.append("")

    parts.append("Ask Jarvis anytime for detail — this brief stays light on purpose.")
    # Trim empty trailing
    text = "\n".join(parts).strip() + "\n"
    return text


def main() -> None:
    env = load_env()
    # Ensure company id available to API helpers
    if env.get("PAPERCLIP_COMPANY_ID"):
        os.environ["PAPERCLIP_COMPANY_ID"] = env["PAPERCLIP_COMPANY_ID"]
    if env.get("OPENCLAW_GATEWAY_URL"):
        os.environ["OPENCLAW_GATEWAY_URL"] = env["OPENCLAW_GATEWAY_URL"]

    brief = build_brief(env)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(TZ).strftime("%Y-%m-%d")
    out_file = REPORT_DIR / f"global-{stamp}.md"
    out_file.write_text(brief, encoding="utf-8")
    print(f"Wrote {out_file}")

    if "--dry-run" in sys.argv:
        print(brief)
        return

    sys.path.insert(0, str(ROOT / "scripts"))
    from clawsum_notify import any_ok, notify_digest  # type: ignore

    results = notify_digest(brief, env=env)
    print(f"Notify results: {results}")
    if not any_ok(results):
        print("ERROR: no channel accepted the brief", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
