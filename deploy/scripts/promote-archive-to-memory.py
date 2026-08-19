#!/usr/bin/env python3
"""
Promote durable facts from ChatGPT archive → ops.memory_facts (+ Arcade) + ops.extracted_facts.

Hard gates:
  - Never process scope=personal
  - Never write secrets into facts
  - Only business|mixed by default (optional --include-unknown)
  - Boss-approved promote pass: sets approved_for_hermes_memory / approved_for_hermes

Usage (VPS):
  python3 promote-archive-to-memory.py --dry-run --limit 20
  python3 promote-archive-to-memory.py --priority-only
  python3 promote-archive-to-memory.py              # full business+mixed
  python3 promote-archive-to-memory.py --resume     # skip already promoted
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Need psycopg2", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path("/docker/clawsum")
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "memory_fact_extract", SCRIPT_DIR / "memory-fact-extract.py"
)
_mfe = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_mfe)

load_env = _mfe.load_env
env_get = _mfe.env_get
pg = _mfe.pg
scrub = _mfe.scrub
validate_fact = _mfe.validate_fact
validate_episode = _mfe.validate_episode
upsert_facts = _mfe.upsert_facts
insert_episodes = _mfe.insert_episodes
mirror_to_arcade = _mfe.mirror_to_arcade
http_json = _mfe.http_json
openrouter_api_key = _mfe.openrouter_api_key
openrouter_enabled = _mfe.openrouter_enabled

try:
    import clawsum_arcade as arcade  # noqa: F401
except Exception:
    arcade = None

BATCH_SYSTEM = """You extract durable memory facts from ChatGPT archive conversation summaries.
Return ONLY valid JSON:
{
  "items": [
    {
      "conversation_id": "uuid",
      "facts": [
        {
          "subject": "Gerald",
          "predicate": "owns|prefers|building|partner|working_on|uses|has_problem|goal|...",
          "object": "short fact object",
          "fact_type": "ownership|preference|goal|relationship|task|problem|project|attribute|observation",
          "importance": "critical|high|medium|low|temporary",
          "confidence": "user_stated|observed|inferred|guessed",
          "scope": "business|mixed|personal",
          "evidence": "short paraphrase"
        }
      ],
      "episodes": [
        {
          "title": "short",
          "summary": "what happened",
          "outcome": "optional",
          "result_state": "open|waiting|done|abandoned",
          "importance": "medium",
          "scope": "business"
        }
      ]
    }
  ]
}

Rules:
- Facts only — not paragraphs. Skip chit-chat and one-off debugging noise.
- Prefer durable preferences, ownership, projects, people, goals, recurring problems, tech stack.
- NEVER include API keys, passwords, tokens, secrets, or full credentials.
- If conversation is personal life only, return empty facts for that id (scope personal → empty).
- Prefer scope=business for company/cell work; mixed only when both; never invent personal details.
- Max 6 facts and 1 episode per conversation. Empty arrays OK.
"""


def call_batch_llm(env: dict, batch_payload: str) -> dict[str, Any]:
    user = f"Extract durable facts from these archive conversations:\n\n{batch_payload[:100000]}"
    openai_key = (env.get("OPENAI_API_KEY") or "").strip()
    model = (env.get("MEMORY_EXTRACT_MODEL") or "").strip()

    if openai_key:
        model = model or "gpt-4.1-mini"
        data = http_json(
            "https://api.openai.com/v1/chat/completions",
            {
                "model": model.replace("openai/", ""),
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": BATCH_SYSTEM},
                    {"role": "user", "content": user},
                ],
            },
            {"Authorization": f"Bearer {openai_key}"},
            timeout=180,
        )
    elif openrouter_enabled():
        model = model or "google/gemini-2.5-flash"
        if model.startswith("openrouter/"):
            model = model[len("openrouter/") :]
        data = http_json(
            "https://openrouter.ai/api/v1/chat/completions",
            {
                "model": model,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": BATCH_SYSTEM},
                    {"role": "user", "content": user},
                ],
            },
            {
                "Authorization": f"Bearer {openrouter_api_key()}",
                "HTTP-Referer": "https://clawsum.com",
                "X-Title": "Clawsum Archive→Memory",
            },
            timeout=180,
        )
    else:
        raise RuntimeError("Need OPENAI_API_KEY or OPENROUTER_API_KEY")

    content = (
        ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    ).strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise RuntimeError("batch JSON root must be object")
    parsed.setdefault("items", [])
    return parsed


def fetch_candidates(conn, *, priority_only: bool, include_unknown: bool, resume: bool, limit: int):
    scopes = ["business", "mixed"]
    if include_unknown:
        scopes.append("unknown")
    sql = """
        SELECT c.id::text AS id, c.title, c.scope, c.work_status, c.intent_summary,
               c.message_count, c.sensitivity_level
        FROM ops.conversations c
        WHERE c.scope = ANY(%s)
          AND c.scope <> 'personal'
          AND COALESCE(c.sensitivity_level, '') <> 'redact'
    """
    params: list[Any] = [scopes]
    if priority_only:
        sql += " AND c.work_status IN ('pending', 'blocked', 'in_progress')"
    if resume:
        sql += """
          AND NOT EXISTS (
            SELECT 1 FROM ops.memory_facts mf
            WHERE mf.source_kind = 'chatgpt' AND mf.source_ref = c.id::text
          )
          AND NOT EXISTS (
            SELECT 1 FROM ops.extracted_facts ef
            WHERE ef.source_conversation_id = c.id
              AND ef.fact_text LIKE '[archive-promote:%%'
          )
        """
    sql += """
        ORDER BY
          CASE c.work_status
            WHEN 'blocked' THEN 0
            WHEN 'pending' THEN 1
            WHEN 'in_progress' THEN 2
            ELSE 3
          END,
          CASE c.scope WHEN 'business' THEN 0 WHEN 'mixed' THEN 1 ELSE 2 END,
          c.updated_at_source DESC NULLS LAST
    """
    if limit:
        sql += " LIMIT %s"
        params.append(limit)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def sample_messages(conn, conversation_id: str, max_chars: int = 1800) -> str:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT role, content FROM ops.messages
            WHERE conversation_id = %s::uuid
            ORDER BY message_order ASC NULLS LAST, created_at_source ASC NULLS LAST
            LIMIT 12
            """,
            (conversation_id,),
        )
        parts = []
        total = 0
        for row in cur.fetchall():
            piece = f"{row['role']}: {scrub(row['content'] or '')}"
            if total + len(piece) > max_chars:
                piece = piece[: max(0, max_chars - total)]
            parts.append(piece)
            total += len(piece)
            if total >= max_chars:
                break
        return "\n".join(parts)


def build_batch_text(conn, rows: list[dict]) -> str:
    blocks = []
    for r in rows:
        body = sample_messages(conn, r["id"])
        blocks.append(
            json.dumps(
                {
                    "conversation_id": r["id"],
                    "title": r.get("title") or "",
                    "scope": r.get("scope"),
                    "work_status": r.get("work_status"),
                    "intent_summary": r.get("intent_summary") or "",
                    "excerpt": body,
                },
                ensure_ascii=False,
            )
        )
    return "\n---\n".join(blocks)


def save_extracted_facts(conn, conversation_id: str, facts: list[dict], approve: bool) -> int:
    n = 0
    with conn.cursor() as cur:
        for f in facts:
            text = f"{f['subject']} {f['predicate']} {f['object']}"
            cur.execute(
                """
                INSERT INTO ops.extracted_facts (
                  source_conversation_id, fact_text, fact_type, confidence,
                  durable, approved_for_hermes_memory
                ) VALUES (%s::uuid, %s, %s, %s, %s, %s)
                """,
                (
                    conversation_id,
                    text[:2000],
                    f.get("fact_type"),
                    {"user_stated": 0.9, "observed": 0.8, "confirmed": 0.95, "inferred": 0.55, "guessed": 0.3}.get(
                        f.get("confidence"), 0.5
                    ),
                    f.get("importance") in ("critical", "high", "medium"),
                    approve and f.get("scope") != "personal",
                ),
            )
            n += 1
    conn.commit()
    return n


def mark_conversation_approved(conn, conversation_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ops.conversations
            SET approved_for_hermes = true, updated_at = now()
            WHERE id = %s::uuid
            """,
            (conversation_id,),
        )
    conn.commit()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--priority-only", action="store_true")
    ap.add_argument("--include-unknown", action="store_true")
    ap.add_argument("--resume", action="store_true", default=True)
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-arcade", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.4)
    args = ap.parse_args()
    resume = False if args.no_resume else args.resume

    env = load_env()
    source_host = env_get("CLAWSUM_SOURCE_HOST", "vps")
    conn = pg(env)

    rows = fetch_candidates(
        conn,
        priority_only=args.priority_only,
        include_unknown=args.include_unknown,
        resume=resume,
        limit=args.limit,
    )
    print(
        json.dumps(
            {
                "candidates": len(rows),
                "priority_only": args.priority_only,
                "include_unknown": args.include_unknown,
                "resume": resume,
                "dry_run": args.dry_run,
            }
        ),
        flush=True,
    )
    if not rows:
        print("Nothing to promote")
        return 0
    if args.dry_run:
        for r in rows[:25]:
            print(f"- [{r['work_status']}/{r['scope']}] {r['title'][:70]}")
        return 0

    stats = {
        "conversations": 0,
        "facts": 0,
        "episodes": 0,
        "extracted_rows": 0,
        "arcade": 0,
        "batches_ok": 0,
        "batches_fail": 0,
    }

    batch_size = max(1, min(args.batch_size, 12))
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        print(f"batch {i // batch_size + 1}/{(len(rows) + batch_size - 1) // batch_size} size={len(batch)}", flush=True)
        try:
            payload = build_batch_text(conn, batch)
            parsed = call_batch_llm(env, payload)
        except Exception as exc:
            stats["batches_fail"] += 1
            print(f"batch fail: {exc}", file=sys.stderr, flush=True)
            time.sleep(max(args.sleep, 1.0))
            continue

        by_id = {str(it.get("conversation_id")): it for it in (parsed.get("items") or []) if isinstance(it, dict)}
        for r in batch:
            cid = r["id"]
            item = by_id.get(cid) or {}
            facts = [
                f
                for f in (validate_fact(x) for x in (item.get("facts") or []))
                if f and f.get("scope") != "personal"
            ]
            # Force non-personal scope for this promote pass
            for f in facts:
                if f["scope"] not in ("business", "mixed"):
                    f["scope"] = "business" if r.get("scope") == "business" else (r.get("scope") or "business")
            episodes = [
                e
                for e in (validate_episode(x) for x in (item.get("episodes") or []))
                if e and e.get("scope") != "personal"
            ]

            fact_ids: list[str] = []
            if facts:
                fact_ids = upsert_facts(
                    conn,
                    facts,
                    source_host=source_host,
                    source_kind="chatgpt",
                    source_ref=cid,
                    source_agent="archive-promote",
                )
                stats["facts"] += len(fact_ids)
                stats["extracted_rows"] += save_extracted_facts(conn, cid, facts, approve=True)
                mark_conversation_approved(conn, cid)
            else:
                # Resume marker so empty conversations are not retried forever
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ops.extracted_facts (
                          source_conversation_id, fact_text, fact_type, durable, approved_for_hermes_memory
                        ) VALUES (%s::uuid, %s, 'marker', false, false)
                        """,
                        (cid, "[archive-promote: no durable facts]"),
                    )
                conn.commit()
                stats["extracted_rows"] += 1

            episode_ids: list[str] = []
            if episodes:
                episode_ids = insert_episodes(
                    conn,
                    episodes,
                    source_host=source_host,
                    source_kind="chatgpt",
                    source_ref=cid,
                    fact_ids=fact_ids,
                )
                stats["episodes"] += len(episode_ids)

            if not args.no_arcade and (fact_ids or episode_ids):
                try:
                    stats["arcade"] += mirror_to_arcade(conn, fact_ids, episode_ids)
                except Exception as exc:
                    print(f"arcade warn: {exc}", file=sys.stderr)

            stats["conversations"] += 1

        stats["batches_ok"] += 1
        print(json.dumps({"progress": stats}), flush=True)
        time.sleep(args.sleep)

    # dream run log
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ops.memory_dream_runs (stage, source_host, finished_at, ok, stats, notes)
            VALUES ('immediate', %s, now(), true, %s::jsonb, %s)
            """,
            (source_host, json.dumps(stats), "promote-archive-to-memory"),
        )
    conn.commit()
    conn.close()
    print(json.dumps({"ok": True, **stats}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
