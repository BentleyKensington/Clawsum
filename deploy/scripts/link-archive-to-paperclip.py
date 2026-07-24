#!/usr/bin/env python3
"""
Link classified archive conversations to Paperclip issues by title/keyword overlap.
Updates work_status from live Paperclip status when a link is found.

Usage:
  python3 link-archive-to-paperclip.py
  python3 link-archive-to-paperclip.py --min-score 2
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
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


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]{3,}", (text or "").lower())
    stop = {"the", "and", "for", "with", "that", "this", "from", "have", "will", "your", "about"}
    return {w for w in words if w not in stop}


def map_paperclip_status(status: str | None) -> str:
    s = (status or "").lower()
    if s in ("done", "cancelled"):
        return "completed" if s == "done" else "abandoned"
    if s in ("in_progress", "in_review", "todo"):
        return "in_progress" if s != "todo" else "pending"
    if s == "blocked":
        return "blocked"
    if s == "backlog":
        return "pending"
    return "other"


def fetch_issues(api: str, company: str) -> list[dict]:
    issues: list[dict] = []
    for status in ("backlog", "todo", "in_progress", "in_review", "blocked", "done"):
        url = f"{api.rstrip('/')}/companies/{company}/issues?status={status}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            item["_status"] = status
                            issues.append(item)
        except Exception as exc:
            print(f"warn fetch {status}: {exc}", file=sys.stderr)
    return issues


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    env = load_env()
    api = env.get("PAPERCLIP_API", "http://127.0.0.1:3100/api")
    company = env.get("PAPERCLIP_COMPANY_ID", "").strip()
    if not company:
        raise SystemExit("PAPERCLIP_COMPANY_ID required in .env")

    issues = fetch_issues(api, company)
    print(f"Paperclip issues loaded: {len(issues)}")
    issue_index = []
    for iss in issues:
        title = iss.get("title") or iss.get("name") or ""
        ident = iss.get("identifier") or iss.get("key") or ""
        issue_index.append(
            {
                "id": str(iss.get("id") or ""),
                "identifier": str(ident),
                "title": title,
                "status": iss.get("_status") or iss.get("status"),
                "tokens": tokens(f"{ident} {title}"),
            }
        )

    conn = connect()
    linked = 0
    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            sql = """
                SELECT id, title, intent_summary, scope, work_status
                FROM ops.conversations
                WHERE scope IN ('business', 'mixed', 'unknown')
                ORDER BY updated_at_source DESC NULLS LAST
            """
            if args.limit:
                sql += f" LIMIT {int(args.limit)}"
            cur.execute(sql)
            rows = cur.fetchall()

            for row in rows:
                ct = tokens(f"{row['title']} {row.get('intent_summary') or ''}")
                if not ct:
                    continue
                best = None
                best_score = 0
                for iss in issue_index:
                    score = len(ct & iss["tokens"])
                    # boost exact identifier mention
                    if iss["identifier"] and iss["identifier"].lower() in (row["title"] or "").lower():
                        score += 5
                    if score > best_score:
                        best_score = score
                        best = iss
                if not best or best_score < args.min_score:
                    continue

                cur.execute("DELETE FROM ops.archive_task_links WHERE conversation_id = %s", (row["id"],))
                cur.execute(
                    """
                    INSERT INTO ops.archive_task_links (
                      conversation_id, paperclip_issue_id, paperclip_identifier,
                      paperclip_title, paperclip_status, match_reason, confidence
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        row["id"],
                        best["id"],
                        best["identifier"],
                        best["title"],
                        best["status"],
                        f"token_overlap={best_score}",
                        min(1.0, best_score / 8.0),
                    ),
                )
                mapped = map_paperclip_status(best["status"])
                # Prefer Paperclip truth when linked
                cur.execute(
                    """
                    UPDATE ops.conversations SET
                      paperclip_issue_id = %s,
                      paperclip_issue_identifier = %s,
                      link_confidence = %s,
                      work_status = %s,
                      updated_at = now(),
                      proactive_flags = array(
                        SELECT DISTINCT x FROM unnest(
                          COALESCE(proactive_flags, '{}') || ARRAY['linked_paperclip']
                        ) AS x
                      )
                    WHERE id = %s
                    """,
                    (best["id"], best["identifier"], min(1.0, best_score / 8.0), mapped, row["id"]),
                )
                linked += 1

            cur.execute(
                """
                UPDATE ops.chatgpt_imports
                SET import_status = 'linked'
                WHERE import_status IN ('parsed', 'classified')
                """
            )

    print(json.dumps({"linked": linked, "issues_scanned": len(issues)}, indent=2))


if __name__ == "__main__":
    main()
