#!/usr/bin/env python3
"""
Build a proactive brief from ChatGPT archive + Paperclip links.

Hermes / CEO brief should ask clarifying questions and drive pending work —
never dump raw history into memory.

Usage:
  python3 archive-proactive-brief.py
  python3 archive-proactive-brief.py --json > /tmp/archive-brief.json
  python3 archive-proactive-brief.py --markdown
"""
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
    print("Need psycopg2", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    out.update(os.environ)
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


def build_brief(limit: int = 12) -> dict:
    conn = connect()
    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT scope, work_status, count(*) AS n
                FROM ops.conversations
                GROUP BY 1, 2
                ORDER BY 1, 2
                """
            )
            counts = [dict(r) for r in cur.fetchall()]

            cur.execute(
                """
                SELECT c.id, c.title, c.scope, c.work_status, c.intent_summary,
                       c.clarification_questions, c.proactive_flags,
                       c.paperclip_issue_identifier, b.slug AS business_slug
                FROM ops.conversations c
                LEFT JOIN ops.businesses b ON b.id = c.primary_business_id
                WHERE c.scope IN ('business', 'mixed', 'unknown')
                  AND c.work_status IN ('pending', 'blocked', 'in_progress', 'other')
                  AND COALESCE(array_length(c.clarification_questions, 1), 0) > 0
                ORDER BY
                  CASE c.work_status
                    WHEN 'blocked' THEN 0
                    WHEN 'pending' THEN 1
                    WHEN 'in_progress' THEN 2
                    ELSE 3
                  END,
                  c.updated_at_source DESC NULLS LAST
                LIMIT %s
                """,
                (limit,),
            )
            drive = []
            for r in cur.fetchall():
                item = dict(r)
                item["id"] = str(item["id"])
                drive.append(item)

            cur.execute(
                """
                SELECT count(*) AS n FROM ops.conversations WHERE scope = 'personal'
                """
            )
            personal_n = int(cur.fetchone()["n"])

            cur.execute(
                """
                SELECT et.task_text, et.status, b.slug AS business_slug, c.title AS source_title
                FROM ops.extracted_tasks et
                LEFT JOIN ops.businesses b ON b.id = et.business_id
                LEFT JOIN ops.conversations c ON c.id = et.source_conversation_id
                WHERE et.status = 'proposed'
                ORDER BY et.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            proposed = [dict(r) for r in cur.fetchall()]

    questions: list[str] = []
    for item in drive:
        for q in item.get("clarification_questions") or []:
            if q and q not in questions:
                questions.append(q)
        if len(questions) >= 8:
            break

    hermes_instructions = [
        "Read the Paperclip task list first; do not invent work outside it.",
        "Cross-link archive items that share intent with open issues; say the identifier when linked.",
        "Treat scope=personal as private — do not push into business agents or Hermes durable memory.",
        "For each pending/blocked/unknown business item, ask one sharp clarifying question before acting.",
        "Propose the next concrete Paperclip action (create/update/link issue) and wait for Boss approval when risk is non-trivial.",
        "Never dump ChatGPT history wholesale into memory — only approved facts/chunks.",
    ]

    return {
        "ok": True,
        "counts_by_scope_status": counts,
        "personal_conversations": personal_n,
        "drive_forward": drive,
        "proposed_tasks": proposed,
        "questions_for_boss": questions,
        "hermes_instructions": hermes_instructions,
    }


def to_markdown(brief: dict) -> str:
    lines = [
        "# Proactive archive brief",
        "",
        "## Hermes standing orders",
    ]
    for i in brief["hermes_instructions"]:
        lines.append(f"- {i}")
    lines += ["", "## Ask Boss next"]
    for q in brief["questions_for_boss"] or ["(none queued — classify/link archive first)"]:
        lines.append(f"- {q}")
    lines += ["", "## Drive-forward items"]
    if not brief["drive_forward"]:
        lines.append("- (none)")
    for item in brief["drive_forward"]:
        link = item.get("paperclip_issue_identifier") or "unlinked"
        cell = item.get("business_slug") or item.get("scope")
        lines.append(
            f"- [{item.get('work_status')}] ({cell}) {item.get('title')} — Paperclip: {link}"
        )
        for q in (item.get("clarification_questions") or [])[:2]:
            lines.append(f"  - Q: {q}")
    lines += ["", f"Personal archives held private: {brief['personal_conversations']}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()
    brief = build_brief(limit=args.limit)
    if args.markdown and not args.json:
        sys.stdout.write(to_markdown(brief))
    else:
        print(json.dumps(brief, indent=2, default=str))


if __name__ == "__main__":
    main()
