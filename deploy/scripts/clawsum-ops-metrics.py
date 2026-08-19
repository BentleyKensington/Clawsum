#!/usr/bin/env python3
"""Export low-cardinality Clawsum workload metrics for node_exporter's textfile collector."""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
OUT = ROOT / "data" / "prometheus-textfile" / "clawsum_ops.prom"
ENV_FILE = ROOT / ".env"


def load_env() -> dict[str, str]:
    result: dict[str, str] = {}
    if not ENV_FILE.is_file():
        return result
    for raw in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


ENV = load_env()


def label(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def query(sql: str) -> list[list[str]]:
    user = ENV.get("POSTGRES_USER", "clawsum")
    database = ENV.get("POSTGRES_DB", "clawsum")
    try:
        result = subprocess.run(
            [
                "docker", "exec", "clawsum-postgres-1", "psql",
                "-U", user, "-d", database, "-t", "-A", "-F", "|", "-c", sql,
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode != 0:
            return []
        return [
            row.split("|")
            for row in result.stdout.splitlines()
            if row.strip()
        ]
    except (OSError, subprocess.SubprocessError):
        return []


def get_json(url: str) -> object | None:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def main() -> int:
    lines = [
        "# HELP clawsum_ops_metrics_generated_timestamp_seconds Last successful textfile generation.",
        "# TYPE clawsum_ops_metrics_generated_timestamp_seconds gauge",
        f"clawsum_ops_metrics_generated_timestamp_seconds {time.time():.3f}",
    ]

    authority_path = (
        ROOT
        / "examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/authority.json"
    )
    try:
        authority = json.loads(authority_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        authority = {}
    lines.append(f"clawsum_authority_agents {len(authority.get('agents') or [])}")
    lines.append(f"clawsum_authority_skills {len(authority.get('skills') or [])}")

    db_up = bool(query("SELECT 1"))
    lines.append(f"clawsum_postgres_up {1 if db_up else 0}")
    if db_up:
        for status, count in query(
            "SELECT processing_status, count(*) FROM ops.emails GROUP BY 1"
        ):
            lines.append(
                f'clawsum_emails{{processing_status="{label(status)}"}} {int(count)}'
            )
        for status, count in query(
            "SELECT COALESCE(review_status, 'unreviewed'), count(*) "
            "FROM ops.emails GROUP BY 1"
        ):
            lines.append(
                f'clawsum_email_reviews{{review_status="{label(status)}"}} {int(count)}'
            )
        sync = query(
            "SELECT COALESCE(EXTRACT(EPOCH FROM (now() - last_sync_at)), -1), "
            "messages_total FROM ops.email_sync_state WHERE id=1"
        )
        if sync:
            lines.append(f"clawsum_gmail_sync_age_seconds {float(sync[0][0]):.3f}")
            lines.append(f"clawsum_gmail_messages_total {int(sync[0][1])}")
        for status, count in query(
            "SELECT status, count(*) FROM ops.approvals GROUP BY 1"
        ):
            lines.append(
                f'clawsum_approvals{{status="{label(status)}"}} {int(count)}'
            )
        cells = query("SELECT count(*) FROM ops.businesses WHERE active")
        if cells:
            lines.append(f"clawsum_business_cells_active {int(cells[0][0])}")
        audit = query(
            "SELECT count(*) FROM ops.audit_logs "
            "WHERE created_at >= now() - interval '24 hours'"
        )
        if audit:
            lines.append(f"clawsum_audit_events_24h {int(audit[0][0])}")

    api = ENV.get("PAPERCLIP_API", "http://127.0.0.1:3100/api").rstrip("/")
    company = ENV.get("PAPERCLIP_COMPANY_ID", "")
    health = get_json(f"{api}/health")
    lines.append(f"clawsum_paperclip_api_up {1 if health is not None else 0}")
    if company:
        for status in ("backlog", "todo", "in_progress", "blocked", "done"):
            issues = get_json(f"{api}/companies/{company}/issues?status={status}")
            if isinstance(issues, list):
                lines.append(
                    f'clawsum_paperclip_issues{{status="{status}"}} {len(issues)}'
                )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT.with_suffix(".prom.tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
