#!/usr/bin/env python3
"""Build and send Clawsum 24h global status report (7am America/Chicago cron)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
REPORT_DIR = ROOT / "data" / "reports"
TZ = ZoneInfo("America/Chicago")
PAPERCLIP_API = os.environ.get("PAPERCLIP_API", "http://127.0.0.1:3100/api")
PAPERCLIP_COMPANY_ID = os.environ.get(
    "PAPERCLIP_COMPANY_ID", ""
)
GATEWAY_HEALTH = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:48166") + "/healthz"
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://127.0.0.1:9090")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENV_FILE.exists():
        return out
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def http_get(url: str, timeout: int = 10) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode(errors="replace")[:4000]
    except Exception as e:
        return 0, str(e)


def _parse_issues(body: str) -> list:
    try:
        data = json.loads(body)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def paperclip_summary() -> str:
    code, body = http_get(f"{PAPERCLIP_API}/health")
    lines = ["📋 Paperclip / tasks", f"API: {code}"]
    if code != 200:
        return "\n".join(lines)

    code, dash_body = http_get(f"{PAPERCLIP_API}/companies/{PAPERCLIP_COMPANY_ID}/dashboard")
    if code == 200:
        try:
            d = json.loads(dash_body)
            agents = d.get("agents") or d.get("agentCounts") or {}
            tasks = d.get("tasks") or d.get("issueCounts") or {}
            costs = d.get("costs") or d.get("costSummary") or {}
            lines.append(f"Agents: {json.dumps(agents)[:180]}")
            lines.append(f"Tasks: {json.dumps(tasks)[:180]}")
            if costs:
                spend = costs.get("monthSpendCents", costs)
                budget = costs.get("monthBudgetCents", "")
                lines.append(f"Spend: {spend} / budget {budget} cents")
        except json.JSONDecodeError:
            lines.append("Dashboard: (parse error)")

    for status, label in [
        ("in_progress", "In progress"),
        ("todo,backlog", "Todo/backlog"),
        ("blocked", "Blocked"),
        ("done", "Done (sample)"),
    ]:
        code_i, issues_body = http_get(
            f"{PAPERCLIP_API}/companies/{PAPERCLIP_COMPANY_ID}/issues?status={status}"
        )
        if code_i != 200:
            continue
        issues = _parse_issues(issues_body)
        if not issues:
            continue
        lines.append(f"{label} ({len(issues)}):")
        for i in issues[:5]:
            title = (i.get("title") or "?")[:55]
            st = i.get("status", "?")
            aid = (i.get("assigneeAgentId") or "unassigned")[:8]
            lines.append(f"  • [{st}] {title} ({aid}…)")
        if len(issues) > 5:
            lines.append(f"  … +{len(issues) - 5} in Boss UI")

    code_act, act_body = http_get(
        f"{PAPERCLIP_API}/companies/{PAPERCLIP_COMPANY_ID}/activity"
    )
    if code_act == 200:
        try:
            activity = json.loads(act_body)
            if isinstance(activity, list) and activity:
                lines.append(f"Recent activity ({min(len(activity), 5)} shown):")
                for ev in activity[:5]:
                    kind = ev.get("action") or ev.get("type") or "event"
                    who = ev.get("agentId") or ev.get("actor") or ""
                    lines.append(f"  • {kind} {who}"[:80])
        except json.JSONDecodeError:
            pass

    return "\n".join(lines)


def _psql_query(sql: str) -> str | None:
    env = load_env()
    user = env.get("POSTGRES_USER", "clawsum")
    db = env.get("POSTGRES_DB", "clawsum")
    try:
        out = subprocess.run(
            [
                "docker",
                "exec",
                "clawsum-postgres-1",
                "psql",
                "-U",
                user,
                "-d",
                db,
                "-t",
                "-A",
                "-c",
                sql,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if out.returncode == 0:
            return (out.stdout or "").strip()
    except Exception:
        pass
    return None


def email_summary() -> str:
    lines = ["📧 Gmail archive (admin)"]
    exists = _psql_query("SELECT to_regclass('ops.emails')::text")
    if not exists or exists == "":
        lines.append("  Schema not applied — run 05-ops-email.sql")
        lines.append("  Setup: docs/GMAIL-ADMIN-SETUP.md")
        return "\n".join(lines)

    counts = _psql_query(
        "SELECT processing_status || ':' || COUNT(*) FROM ops.emails GROUP BY 1"
    )
    if counts:
        lines.append("By status:")
        for row in counts.splitlines():
            if ":" in row:
                st, n = row.split(":", 1)
                lines.append(f"  {st}: {n}")

    last24 = _psql_query(
        "SELECT COUNT(*) FROM ops.emails WHERE received_at > NOW() - INTERVAL '24 hours'"
    )
    if last24:
        lines.append(f"Received last 24h: {last24}")

    pending = _psql_query(
        "SELECT subject || ' <- ' || COALESCE(from_addr,'') FROM ops.emails "
        "WHERE processing_status = 'pending' ORDER BY received_at DESC LIMIT 5"
    )
    if pending:
        lines.append("Pending triage (latest):")
        for row in pending.splitlines()[:5]:
            lines.append(f"  • {row[:75]}")
    else:
        lines.append("Pending triage: 0")

    sync = _psql_query(
        "SELECT COALESCE(last_sync_at::text,'never') || ' | total=' || messages_total::text "
        "FROM ops.email_sync_state WHERE id=1"
    )
    if sync:
        lines.append(f"Sync: {sync}")
    else:
        lines.append("Sync: not started — add Gmail OAuth then gmail-sync.py --backfill")

    return "\n".join(lines)


def docker_status() -> str:
    try:
        out = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "name=clawsum",
                "--format",
                "{{.Names}}\t{{.Status}}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        lines = ["Containers:"]
        for row in (out.stdout or "").strip().splitlines():
            if row.strip():
                lines.append(f"  {row}")
        if not lines[1:]:
            lines.append("  (none running)")
        return "\n".join(lines)
    except Exception as e:
        return f"Containers: error {e}"


def gateway_status() -> str:
    code, _ = http_get(GATEWAY_HEALTH)
    return f"OpenClaw gateway: {'OK' if code == 200 else f'FAIL ({code})'}"


def prometheus_status() -> str:
    code, body = http_get(f"{PROMETHEUS_URL}/api/v1/targets")
    if code != 200:
        return "Prometheus: not running (enable: docker compose --profile monitoring up -d)"
    try:
        data = json.loads(body)
        active = data.get("data", {}).get("activeTargets", [])
        up = sum(1 for t in active if t.get("health") == "up")
        return f"Prometheus: {up}/{len(active)} targets up"
    except json.JSONDecodeError:
        return "Prometheus: running"


def log_errors_24h() -> str:
    lines = ["Recent errors (gateway log, ~24h):"]
    try:
        out = subprocess.run(
            [
                "docker",
                "exec",
                "clawsum-openclaw-gateway-1",
                "sh",
                "-c",
                "grep -iE 'error|fail|EACCES|readonly' /tmp/openclaw/openclaw-*.log 2>/dev/null | tail -12",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        chunk = (out.stdout or "").strip()
        if not chunk:
            lines.append("  (none in tail)")
        else:
            for row in chunk.splitlines()[-8:]:
                # strip JSON noise for telegram
                msg = row
                if '"message":"' in row:
                    m = re.search(r'"message":"([^"]{0,120})', row)
                    if m:
                        msg = m.group(1)
                lines.append(f"  {msg[:140]}")
    except Exception as e:
        lines.append(f"  (log scan failed: {e})")
    return "\n".join(lines)


def disk_status() -> str:
    try:
        out = subprocess.run(["df", "-h", "/docker/clawsum"], capture_output=True, text=True, timeout=10)
        return "Disk:\n" + (out.stdout or "").strip()
    except Exception as e:
        return f"Disk: {e}"


def reminders_summary() -> str:
    lines = ["⏰ Reminders"]
    active = _psql_query(
        "SELECT COUNT(*) FROM ops.reminders WHERE completed_at IS NULL "
        "AND (snoozed_until IS NULL OR snoozed_until < CURRENT_DATE) AND remind_daily = TRUE"
    )
    overdue = _psql_query(
        "SELECT COUNT(*) FROM ops.reminders WHERE completed_at IS NULL "
        "AND due_date < CURRENT_DATE AND (snoozed_until IS NULL OR snoozed_until < CURRENT_DATE)"
    )
    if active is None:
        lines.append("  (schema not applied — run 06-ops-reminders.sql)")
        return "\n".join(lines)
    lines.append(f"  Active (daily nudge): {active or '0'}")
    if overdue and int(overdue or 0) > 0:
        lines.append(f"  Overdue: {overdue}")
    sample = _psql_query(
        "SELECT title FROM ops.reminders WHERE completed_at IS NULL "
        "AND (snoozed_until IS NULL OR snoozed_until < CURRENT_DATE) "
        "ORDER BY due_date NULLS LAST LIMIT 3"
    )
    if sample:
        for row in sample.splitlines()[:3]:
            lines.append(f"  • {row[:60]}")
    return "\n".join(lines)


def build_report() -> str:
    now = datetime.now(TZ)
    parts = [
        f"📊 Clawsum Global Report",
        f"{now.strftime('%A %Y-%m-%d %H:%M %Z')}",
        "",
        gateway_status(),
        docker_status(),
        "",
        paperclip_summary(),
        "",
        reminders_summary(),
        "",
        email_summary(),
        "",
        prometheus_status(),
        "",
        disk_status(),
        "",
        log_errors_24h(),
        "",
        "Boss UI: ssh -L 3100:127.0.0.1:3100 clawsum → http://localhost:3100",
        "Grafana: ssh -L 3000:127.0.0.1:3000 clawsum → http://localhost:3000",
    ]
    return "\n".join(parts)


def send_telegram(text: str, token: str, chat_id: str) -> None:
    # Telegram limit 4096; split if needed
    chunks = []
    while text:
        chunks.append(text[:3900])
        text = text[3900:]
    for chunk in chunks:
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
                raise RuntimeError(result)


def main() -> None:
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    # CS Ops group (admin) default; override with TELEGRAM_REPORT_CHAT_ID for DM
    chat_id = (
        env.get("TELEGRAM_REPORT_CHAT_ID")
        or os.environ.get("TELEGRAM_REPORT_CHAT_ID")
        or ""
    )

    report = build_report()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(TZ).strftime("%Y-%m-%d")
    out_file = REPORT_DIR / f"global-{stamp}.md"
    out_file.write_text(report + "\n", encoding="utf-8")
    print(f"Wrote {out_file}")

    if "--dry-run" in sys.argv:
        print(report)
        return

    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN missing", file=sys.stderr)
        sys.exit(1)

    send_telegram(report, token, chat_id)
    print(f"Sent to Telegram chat {chat_id}")


if __name__ == "__main__":
    main()
