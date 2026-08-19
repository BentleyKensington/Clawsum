#!/usr/bin/env python3
"""Link recent Gmail (ops.emails) to Paperclip issues and ChatGPT archive by overlap.

  python3 gmail-task-link.py --markdown
"""
from __future__ import annotations

import argparse
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # type: ignore

TZ = ZoneInfo("America/Chicago")
STOP = {
    "the",
    "and",
    "for",
    "you",
    "your",
    "this",
    "that",
    "from",
    "with",
    "have",
    "are",
    "was",
    "re",
    "fwd",
}


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


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]{4,}", (text or "").lower())
    return {w for w in words if w not in STOP}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--days", type=int, default=14)
    args = ap.parse_args()
    if not psycopg2:
        print("psycopg2 missing — skip gmail-task-link")
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
    since = datetime.now(TZ) - timedelta(days=args.days)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    emails = []
    try:
        cur.execute(
            """
            SELECT id, subject, from_addr, snippet, received_at
            FROM ops.emails
            WHERE received_at >= %s
            ORDER BY received_at DESC
            LIMIT 80
            """,
            (since,),
        )
        emails = list(cur.fetchall())
    except Exception as e:
        print(f"ops.emails not queryable: {e}")
        conn.close()
        return 0

    convos = []
    try:
        cur.execute(
            """
            SELECT id, title, scope, work_status, paperclip_issue_id
            FROM ops.conversations
            WHERE COALESCE(scope, '') <> 'personal'
            ORDER BY id DESC
            LIMIT 120
            """
        )
        convos = list(cur.fetchall())
    except Exception:
        convos = []

    lines = ["# Gmail ↔ tasks ↔ archive (heuristic)", ""]
    for em in emails:
        subj = em.get("subject") or "(no subject)"
        et = tokens(subj + " " + (em.get("snippet") or ""))
        hits = []
        for cv in convos:
            ct = tokens(cv.get("title") or "")
            overlap = et & ct
            if len(overlap) >= 2:
                pid = cv.get("paperclip_issue_id") or ""
                hits.append(f"{cv.get('title')} (scope={cv.get('scope')} CLA={pid} tokens={sorted(overlap)[:6]})")
        if hits:
            who = em.get("from_addr") or ""
            lines.append(f"- **Mail** `{subj}` from {who}")
            for h in hits[:4]:
                lines.append(f"  - archive: {h}")
    if len(lines) == 2:
        lines.append("_No strong overlaps in the window. Hermes should still read Paperclip first._")
    conn.close()
    print("\n".join(lines) if args.markdown else "\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
