#!/usr/bin/env python3
"""Create an ops.approvals row + audit log (Paperclip overwatch Phase 3)."""
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
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--business", required=True, help="Business slug (e.g. wnn-client)")
    p.add_argument("--action-type", required=True, help="e.g. send_sms")
    p.add_argument("--summary", required=True, help="Action summary")
    p.add_argument("--reason", default="")
    p.add_argument("--risk", default="tier_2", choices=["tier_0", "tier_1", "tier_2", "tier_3"])
    p.add_argument("--agent", default="hermes")
    p.add_argument("--requested-by", default="gerald")
    p.add_argument("--paperclip-issue", default="")
    p.add_argument("--data-accessed", default="", help="Comma-separated")
    p.add_argument("--cost", default="")
    args = p.parse_args()

    if args.risk == "tier_3":
        print("REFUSED: tier_3 is human-only / never autonomous", file=sys.stderr)
        raise SystemExit(2)

    data_accessed = [x.strip() for x in args.data_accessed.split(",") if x.strip()]

    conn = connect()
    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name FROM ops.businesses WHERE slug = %s AND active",
                (args.business,),
            )
            biz = cur.fetchone()
            if not biz:
                print(f"Unknown business slug: {args.business}", file=sys.stderr)
                raise SystemExit(1)

            if args.risk == "tier_0":
                status = "approved"
            else:
                status = "pending"

            cur.execute(
                """
                INSERT INTO ops.approvals (
                  business_id, paperclip_issue_id, requested_by, agent_name,
                  action_type, action_summary, reason, risk_level, data_accessed,
                  cost_estimate, status, approved_by, approved_at
                ) VALUES (
                  %(business_id)s, %(paperclip_issue_id)s, %(requested_by)s, %(agent_name)s,
                  %(action_type)s, %(action_summary)s, %(reason)s, %(risk_level)s, %(data_accessed)s,
                  %(cost_estimate)s, %(status)s,
                  CASE WHEN %(status)s = 'approved' THEN 'auto-tier0' ELSE NULL END,
                  CASE WHEN %(status)s = 'approved' THEN now() ELSE NULL END
                )
                RETURNING id, status, risk_level
                """,
                {
                    "business_id": biz["id"],
                    "paperclip_issue_id": args.paperclip_issue or None,
                    "requested_by": args.requested_by,
                    "agent_name": args.agent,
                    "action_type": args.action_type,
                    "action_summary": args.summary,
                    "reason": args.reason,
                    "risk_level": args.risk,
                    "data_accessed": data_accessed,
                    "cost_estimate": args.cost or None,
                    "status": status,
                },
            )
            row = cur.fetchone()
            cur.execute(
                """
                INSERT INTO ops.audit_logs (
                  business_id, actor_type, actor_name, action, tool_name,
                  input_summary, approval_id, paperclip_issue_id, risk_level
                ) VALUES (
                  %s, 'system', %s, 'approval_created', 'overwatch-create-approval',
                  %s, %s, %s, %s
                )
                """,
                (
                    biz["id"],
                    args.requested_by,
                    args.summary[:500],
                    row["id"],
                    args.paperclip_issue or None,
                    args.risk,
                ),
            )

    print(json.dumps({"approval_id": str(row["id"]), "status": row["status"], "business": biz["name"]}, indent=2))


if __name__ == "__main__":
    main()
