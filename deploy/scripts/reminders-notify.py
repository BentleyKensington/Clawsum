#!/usr/bin/env python3
"""Send Telegram digest of active reminders (due / daily until snoozed or completed)."""
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
TZ = ZoneInfo("America/Chicago")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def psql_rows(sql: str) -> list[str]:
    env = load_env()
    out = subprocess.run(
        [
            "docker", "exec", "clawsum-postgres-1", "psql",
            "-U", env.get("POSTGRES_USER", "clawsum"),
            "-d", env.get("POSTGRES_DB", "clawsum"),
            "-t", "-A", "-F", "\t",
            "-c", sql,
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if out.returncode != 0:
        return []
    rows = []
    for line in (out.stdout or "").strip().splitlines():
        if line.strip():
            rows.append(line)
    return rows


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
            if not json.loads(resp.read().decode()).get("ok"):
                raise RuntimeError("telegram send failed")


def main() -> None:
    today = datetime.now(TZ).date().isoformat()
    lines = [f"⏰ Reminders ({today})", ""]

    active = psql_rows(
        """
        SELECT id, priority, title,
               COALESCE(due_date::text,'—'),
               COALESCE(assigned_agent,'admin')
        FROM ops.reminders
        WHERE completed_at IS NULL
          AND (snoozed_until IS NULL OR snoozed_until < CURRENT_DATE)
          AND remind_daily = TRUE
        ORDER BY
          CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
          due_date NULLS LAST,
          id
        """
    )
    if not active:
        lines.append("No active reminders.")
    else:
        lines.append(f"Active ({len(active)}):")
        for row in active:
            parts = row.split("\t")
            if len(parts) >= 5:
                rid, pri, title, due, agent = parts[0], parts[1], parts[2], parts[3], parts[4]
                lines.append(f"  [{pri}] #{rid} {title[:50]} (due {due}, {agent})")
            else:
                lines.append(f"  • {row[:80]}")

    overdue = psql_rows(
        """
        SELECT COUNT(*) FROM ops.reminders
        WHERE completed_at IS NULL
          AND due_date IS NOT NULL AND due_date < CURRENT_DATE
          AND (snoozed_until IS NULL OR snoozed_until < CURRENT_DATE)
        """
    )
    if overdue and overdue[0].isdigit() and int(overdue[0]) > 0:
        lines.append(f"\n⚠️ Overdue: {overdue[0]}")

    lines.append("\nSnooze SQL: UPDATE ops.reminders SET snoozed_until='YYYY-MM-DD' WHERE id=N;")
    lines.append("Done SQL: UPDATE ops.reminders SET completed_at=NOW() WHERE id=N;")

    report = "\n".join(lines)
    if "--dry-run" in sys.argv:
        print(report)
        return

    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_REPORT_CHAT_ID", "")
    if not token:
        sys.exit("TELEGRAM_BOT_TOKEN missing")
    send_telegram(report, token, chat_id)
    print("Sent reminders digest")


if __name__ == "__main__":
    main()
