#!/usr/bin/env python3
"""
Classify imported ChatGPT conversations:
  - scope: personal | business | mixed | unknown
  - primary business cell (slug match)
  - intent_summary + clarification_questions (heuristic; optional LLM later)
  - work_status cues from conversation text

Usage:
  python3 classify-chatgpt-archive.py
  python3 classify-chatgpt-archive.py --import-id UUID
  python3 classify-chatgpt-archive.py --limit 100
"""
from __future__ import annotations

import argparse
import json
import os
import re
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

BUSINESS_NEEDLES = {
    "wnn-client": ["wnn", "closer appointment", "workshop", "ghl", "closebot", "hyros"],
    "vocalitic": ["vocalitic", "signalwire", "stt", "tts", "latency", "voice ai"],
    "roofing-os": ["roofing", "ceoroof", "hail", "storm", "mrms", "claim"],
    "techtasia": ["techtasia"],
    "acceptai-fastbuy": ["acceptai", "fastbuy", "shopify"],
    "real-estate": ["acquisition", "comp", "listing", "wholesal", "real estate deal"],
    "hardware-local-ai": ["gpu", "vram", "local model", "ollama", "vllm"],
    "personal-admin": ["calendar", "personal email", "family", "doctor", "vacation"],
}

PERSONAL_NEEDLES = [
    "my wife", "my kids", "personal", "family", "birthday", "vacation",
    "doctor", "health insurance", "therapy", "journal",
]

DONE_CUES = [
    r"\b(done|completed|finished|shipped|resolved|closed)\b",
    r"\bmark(ed)? (as )?done\b",
    r"\bno longer needed\b",
]
PENDING_CUES = [
    r"\b(todo|to-do|need to|should|pending|follow[- ]?up|next step)\b",
    r"\bstill (open|waiting|blocked)\b",
    r"\bhaven'?t (yet|started)\b",
]
BLOCKED_CUES = [
    r"\bblocked\b",
    r"\bwaiting on\b",
    r"\bneed(s)? (your|gerald'?s)? approval\b",
]


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


def classify_text(title: str, body: str) -> dict:
    text = f"{title}\n{body}".lower()
    biz_hits: list[tuple[str, int]] = []
    for slug, needles in BUSINESS_NEEDLES.items():
        score = sum(1 for n in needles if n in text)
        if score:
            biz_hits.append((slug, score))
    biz_hits.sort(key=lambda x: -x[1])
    personal_score = sum(1 for n in PERSONAL_NEEDLES if n in text)

    if biz_hits and personal_score:
        scope = "mixed"
    elif biz_hits:
        scope = "business"
    elif personal_score:
        scope = "personal"
    else:
        scope = "unknown"

    primary_slug = biz_hits[0][0] if biz_hits else ("personal-admin" if scope == "personal" else None)

    work = "other"
    if any(re.search(p, text) for p in BLOCKED_CUES):
        work = "blocked"
    elif any(re.search(p, text) for p in DONE_CUES) and not any(re.search(p, text) for p in PENDING_CUES):
        work = "completed"
    elif any(re.search(p, text) for p in PENDING_CUES):
        work = "pending"

    # Intent + questions
    intent = f"Conversation about: {title.strip() or 'untitled topic'}."
    if primary_slug:
        intent += f" Likely cell: {primary_slug}."
    if scope == "personal":
        intent += " Flagged as personal — keep out of business agent memory unless approved."

    questions: list[str] = []
    flags: list[str] = []
    if scope == "unknown":
        questions.append("Is this personal, or which business cell does it belong to?")
        flags.append("needs_scope")
    if work in ("pending", "blocked", "other") and scope in ("business", "mixed", "unknown"):
        questions.append("What is the desired outcome, and is there already a Paperclip task for this?")
        flags.append("needs_outcome")
    if work == "blocked":
        questions.append("What decision or resource would unblock this?")
        flags.append("needs_unblock")
    if not questions and work == "pending":
        questions.append("What is the next concrete action you want Hermes/Paperclip to take?")
        flags.append("needs_next_action")

    return {
        "scope": scope,
        "primary_slug": primary_slug,
        "work_status": work,
        "intent_summary": intent[:1000],
        "clarification_questions": questions[:6],
        "proactive_flags": flags,
        "topics": [s for s, _ in biz_hits[:5]],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--import-id")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--all", action="store_true", help="Reclassify all conversations")
    args = ap.parse_args()

    conn = connect()
    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, slug FROM ops.businesses WHERE active")
            biz_by_slug = {r["slug"]: r["id"] for r in cur.fetchall()}

            where = ["1=1"]
            params: list = []
            if args.import_id:
                where.append("c.import_id = %s")
                params.append(args.import_id)
            if not args.all:
                where.append("(c.scope = 'unknown' OR c.intent_summary IS NULL)")
            sql = f"""
                SELECT c.id, c.title,
                       COALESCE((
                         SELECT string_agg(m.content, E'\\n')
                         FROM (
                           SELECT content FROM ops.messages
                           WHERE conversation_id = c.id
                           ORDER BY message_order
                           LIMIT 12
                         ) m
                       ), '') AS body
                FROM ops.conversations c
                WHERE {' AND '.join(where)}
                ORDER BY c.updated_at_source DESC NULLS LAST
            """
            if args.limit:
                sql += f" LIMIT {int(args.limit)}"
            cur.execute(sql, params)
            rows = cur.fetchall()

            updated = 0
            for row in rows:
                result = classify_text(row["title"] or "", row["body"] or "")
                biz_id = biz_by_slug.get(result["primary_slug"]) if result["primary_slug"] else None
                cur.execute(
                    """
                    UPDATE ops.conversations SET
                      scope = %s,
                      primary_business_id = %s,
                      work_status = %s,
                      intent_summary = %s,
                      clarification_questions = %s,
                      proactive_flags = %s,
                      topics = %s,
                      updated_at = now()
                    WHERE id = %s
                    """,
                    (
                        result["scope"],
                        biz_id,
                        result["work_status"],
                        result["intent_summary"],
                        result["clarification_questions"],
                        result["proactive_flags"],
                        result["topics"],
                        row["id"],
                    ),
                )
                # Extract lightweight proposed tasks from pending business items
                if result["work_status"] in ("pending", "blocked") and result["scope"] in ("business", "mixed"):
                    cur.execute(
                        """
                        INSERT INTO ops.extracted_tasks (business_id, source_conversation_id, task_text, status, priority)
                        SELECT %s, %s, %s, 'proposed', 'normal'
                        WHERE NOT EXISTS (
                          SELECT 1 FROM ops.extracted_tasks
                          WHERE source_conversation_id = %s AND task_text = %s
                        )
                        """,
                        (
                            biz_id,
                            row["id"],
                            f"Drive forward: {row['title']}",
                            row["id"],
                            f"Drive forward: {row['title']}",
                        ),
                    )
                updated += 1

            if args.import_id:
                cur.execute(
                    "UPDATE ops.chatgpt_imports SET import_status = 'classified' WHERE id = %s",
                    (args.import_id,),
                )

    print(json.dumps({"classified": updated}, indent=2))


if __name__ == "__main__":
    main()
