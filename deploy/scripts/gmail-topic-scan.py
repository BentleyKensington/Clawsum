#!/usr/bin/env python3
"""Search ops.emails for a topic (e.g. Deepgram) since a local date.

  python3 gmail-topic-scan.py --query deepgram --since today --markdown
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # type: ignore

TZ = ZoneInfo("America/Chicago")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    p = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum")) / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip() or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    out.update({k: v for k, v in os.environ.items() if v})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--since", default="today", help="today | YYYY-MM-DD | Nd (e.g. 2d)")
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()
    now = datetime.now(TZ)
    if args.since == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif args.since.endswith("d") and args.since[:-1].isdigit():
        start = now - timedelta(days=int(args.since[:-1]))
    else:
        start = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=TZ)
    q = f"%{args.query.lower()}%"
    if not psycopg2:
        print("psycopg2 missing")
        return 0
    env = load_env()
    try:
        conn = psycopg2.connect(
            host=env.get("POSTGRES_HOST", "127.0.0.1"),
            port=int(env.get("POSTGRES_PORT", "5432")),
            user=env.get("POSTGRES_USER", "clawsum"),
            password=env.get("POSTGRES_PASSWORD", ""),
            dbname=env.get("POSTGRES_DB", "clawsum"),
        )
    except Exception as e:
        print(f"postgres unavailable: {e}")
        return 0
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    rows = []
    try:
        cur.execute(
            """
            SELECT id, subject, from_addr, snippet, received_at,
                   COALESCE(has_attachments, false) AS has_attachments
            FROM ops.emails
            WHERE received_at >= %s
              AND (
                lower(coalesce(subject,'')) LIKE %s
                OR lower(coalesce(snippet,'')) LIKE %s
                OR lower(coalesce(from_addr,'')) LIKE %s
              )
            ORDER BY received_at DESC
            LIMIT 40
            """,
            (start, q, q, q),
        )
        rows = list(cur.fetchall())
    except Exception as e:
        # has_attachments may not exist
        try:
            cur.execute(
                """
                SELECT id, subject, from_addr, snippet, received_at
                FROM ops.emails
                WHERE received_at >= %s
                  AND (
                    lower(coalesce(subject,'')) LIKE %s
                    OR lower(coalesce(snippet,'')) LIKE %s
                    OR lower(coalesce(from_addr,'')) LIKE %s
                  )
                ORDER BY received_at DESC
                LIMIT 40
                """,
                (start, q, q, q),
            )
            rows = list(cur.fetchall())
        except Exception as e2:
            print(f"query failed: {e}; fallback: {e2}")
            conn.close()
            return 0
    conn.close()
    lines = [f"# Gmail topic `{args.query}` since {start.isoformat()}", ""]
    if not rows:
        lines.append("_No matching rows in ops.emails. Sync may be paused or mail not ingested._")
    for r in rows:
        att = r.get("has_attachments")
        flag = " attachments=yes" if att else ""
        lines.append(
            f"- {r.get('received_at')} **{r.get('subject')}** from {r.get('from_addr')}{flag}"
        )
        snip = (r.get("snippet") or "").replace("\n", " ")[:240]
        if snip:
            lines.append(f"  - {snip}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
