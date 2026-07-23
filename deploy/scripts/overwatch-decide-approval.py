#!/usr/bin/env python3
"""Approve / reject / revise an ops.approvals row."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Need psycopg2: pip install psycopg2-binary", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        out.setdefault(k, v)
    return out


def connect():
    env = load_env()
    return psycopg2.connect(
        host=env.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(env.get("POSTGRES_PORT", "5432")),
        user=env.get("POSTGRES_USER", "clawsum"),
        password=env.get("POSTGRES_PASSWORD", ""),
        dbname=env.get("POSTGRES_DB", "clawsum"),
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--id", required=True, help="Approval UUID")
    p.add_argument(
        "--decision",
        required=True,
        choices=["approve", "reject", "revise"],
    )
    p.add_argument("--by", default="gerald")
    p.add_argument("--note", default="")
    args = p.parse_args()

    status_map = {
        "approve": "approved",
        "reject": "rejected",
        "revise": "revised",
    }
    status = status_map[args.decision]

    conn = connect()
    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM ops.approvals WHERE id = %s FOR UPDATE",
                (args.id,),
            )
            row = cur.fetchone()
            if not row:
                print("Approval not found", file=sys.stderr)
                raise SystemExit(1)
            if row["status"] != "pending":
                print(f"Not pending (status={row['status']})", file=sys.stderr)
                raise SystemExit(1)
            if row["risk_level"] == "tier_3":
                print("tier_3 cannot be agent-approved", file=sys.stderr)
                raise SystemExit(2)

            cur.execute(
                """
                UPDATE ops.approvals SET
                  status = %s,
                  approved_by = %s,
                  approved_at = CASE WHEN %s = 'approved' THEN now() ELSE approved_at END,
                  rejected_at = CASE WHEN %s = 'rejected' THEN now() ELSE rejected_at END,
                  decision_note = %s
                WHERE id = %s
                RETURNING id, status, action_type, action_summary
                """,
                (status, args.by, status, status, args.note or None, args.id),
            )
            updated = cur.fetchone()
            cur.execute(
                """
                INSERT INTO ops.audit_logs (
                  business_id, actor_type, actor_name, action, tool_name,
                  input_summary, output_summary, approval_id, risk_level
                ) VALUES (
                  %s, 'boss', %s, %s, 'overwatch-decide-approval',
                  %s, %s, %s, %s
                )
                """,
                (
                    row["business_id"],
                    args.by,
                    f"approval_{status}",
                    row["action_summary"],
                    args.note or status,
                    row["id"],
                    row["risk_level"],
                ),
            )

    print(json.dumps(dict(updated), indent=2, default=str))
    if status == "approved":
        print("Next: allow OpenClaw to execute the linked Paperclip task (manual until adapter wired).")


if __name__ == "__main__":
    main()
