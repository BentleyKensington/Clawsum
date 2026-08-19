#!/usr/bin/env python3
"""
Phase 1 memory fact extraction — structured facts → Postgres → ArcadeDB.

Usage (VPS):
  python3 /docker/clawsum/scripts/memory-fact-extract.py \\
    --text "Gerald owns an RTX 4070 Super and prefers self-hosting."
  python3 /docker/clawsum/scripts/memory-fact-extract.py --file note.md
  python3 /docker/clawsum/scripts/memory-fact-extract.py --text "..." --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
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
ENV_FILE = ROOT / ".env"
sys.path.insert(0, str(SCRIPT_DIR))

try:
    import clawsum_arcade as arcade
except Exception:
    arcade = None  # type: ignore

try:
    from llm_policy import env_get, load_env, openrouter_api_key, openrouter_enabled
except Exception:
    def load_env() -> dict[str, str]:
        out: dict[str, str] = {}
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                out[k.strip()] = v.strip().strip('"').strip("'")
        for k, v in os.environ.items():
            out.setdefault(k, v)
        return out

    def env_get(key: str, default: str = "") -> str:
        return (load_env().get(key) or default).strip() or default

    def openrouter_api_key() -> str:
        return env_get("OPENROUTER_API_KEY")

    def openrouter_enabled() -> bool:
        key = openrouter_api_key()
        return bool(key) and key.startswith("sk-or-")


SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|password|secret|token|bearer\s+[a-z0-9\._\-]+|"
    r"sk-[a-z0-9]+|sk-or-[a-z0-9]+)"
)

EXTRACT_SYSTEM = """You extract durable memory facts for a personal AI ops platform.
Return ONLY valid JSON with this shape:
{
  "facts": [
    {
      "subject": "Gerald",
      "predicate": "owns",
      "object": "RTX 4070 Super",
      "fact_type": "ownership",
      "importance": "medium",
      "confidence": "user_stated",
      "scope": "personal",
      "evidence": "short quote or paraphrase"
    }
  ],
  "episodes": [
    {
      "title": "short title",
      "summary": "what happened",
      "outcome": "optional",
      "result_state": "open|waiting|done|abandoned",
      "importance": "medium",
      "scope": "business"
    }
  ]
}

Rules:
- Facts only — no paragraphs as objects.
- predicate: short snake or verb (owns, prefers, building, partner, working_on, has_problem, goal).
- fact_type: ownership|preference|goal|relationship|task|problem|project|attribute|observation
- importance: critical|high|medium|low|temporary
- confidence: observed|confirmed|user_stated|inferred|guessed
- scope: personal|business|mixed|unknown
- Never include API keys, passwords, tokens, or secrets.
- Skip ephemeral chit-chat. Prefer durable preferences, ownership, projects, people, goals.
- If nothing durable, return {"facts":[],"episodes":[]}.
"""


def pg(env: dict):
    return psycopg2.connect(
        host=env.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(env.get("POSTGRES_PORT", "5432") or "5432"),
        user=env.get("POSTGRES_USER", "clawsum"),
        password=env.get("POSTGRES_PASSWORD", ""),
        dbname=env.get("POSTGRES_DB", "clawsum"),
    )


def scrub(text: str) -> str:
    text = SECRET_RE.sub("[REDACTED]", text or "")
    return text.strip()


def norm_key(subject: str, predicate: str, obj: str) -> str:
    raw = "|".join(
        re.sub(r"\s+", " ", (x or "").strip().lower())
        for x in (predicate, subject, obj)
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def http_json(url: str, payload: dict, headers: dict, timeout: int = 90) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST", headers={**headers, "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode() if e.fp else str(e)
        raise RuntimeError(f"HTTP {e.code}: {err[:500]}") from e


def call_llm(env: dict, text: str) -> dict[str, Any]:
    user = f"Extract memory facts from:\n\n{text[:12000]}"
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
                    {"role": "system", "content": EXTRACT_SYSTEM},
                    {"role": "user", "content": user},
                ],
            },
            {"Authorization": f"Bearer {openai_key}"},
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
                    {"role": "system", "content": EXTRACT_SYSTEM},
                    {"role": "user", "content": user},
                ],
            },
            {
                "Authorization": f"Bearer {openrouter_api_key()}",
                "HTTP-Referer": "https://clawsum.com",
                "X-Title": "Clawsum Memory Extract",
            },
        )
    else:
        raise RuntimeError("Need OPENAI_API_KEY or OPENROUTER_API_KEY for extraction")

    content = (
        ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    ).strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM returned non-JSON: {content[:400]}") from e
    if not isinstance(parsed, dict):
        raise RuntimeError("LLM JSON root must be object")
    parsed.setdefault("facts", [])
    parsed.setdefault("episodes", [])
    return parsed


def validate_fact(f: dict) -> dict | None:
    subject = scrub(str(f.get("subject") or "")).strip()
    predicate = scrub(str(f.get("predicate") or "")).strip().lower().replace(" ", "_")
    obj = scrub(str(f.get("object") or "")).strip()
    if not subject or not predicate or not obj:
        return None
    if len(obj) > 500 or len(subject) > 200:
        return None
    importance = str(f.get("importance") or "medium").lower()
    if importance not in ("critical", "high", "medium", "low", "temporary"):
        importance = "medium"
    confidence = str(f.get("confidence") or "inferred").lower()
    if confidence not in ("observed", "confirmed", "user_stated", "inferred", "guessed"):
        confidence = "inferred"
    scope = str(f.get("scope") or "business").lower()
    if scope not in ("personal", "business", "mixed", "unknown"):
        scope = "business"
    fact_type = scrub(str(f.get("fact_type") or "observation")).lower()[:40] or "observation"
    evidence = scrub(str(f.get("evidence") or ""))[:1000]
    return {
        "subject": subject[:200],
        "predicate": predicate[:80],
        "object": obj[:500],
        "fact_type": fact_type,
        "importance": importance,
        "confidence": confidence,
        "scope": scope,
        "evidence": evidence,
        "fact_key": norm_key(subject, predicate, obj),
    }


def validate_episode(e: dict) -> dict | None:
    title = scrub(str(e.get("title") or "")).strip()
    if not title:
        return None
    importance = str(e.get("importance") or "medium").lower()
    if importance not in ("critical", "high", "medium", "low", "temporary"):
        importance = "medium"
    scope = str(e.get("scope") or "business").lower()
    if scope not in ("personal", "business", "mixed", "unknown"):
        scope = "business"
    result_state = str(e.get("result_state") or "open").lower()
    if result_state not in ("open", "waiting", "done", "abandoned"):
        result_state = "open"
    return {
        "title": title[:300],
        "summary": scrub(str(e.get("summary") or ""))[:4000],
        "outcome": scrub(str(e.get("outcome") or ""))[:2000],
        "result_state": result_state,
        "importance": importance,
        "scope": scope,
    }


def upsert_facts(
    conn,
    facts: list[dict],
    *,
    source_host: str,
    source_kind: str,
    source_ref: str | None,
    source_agent: str | None,
) -> list[str]:
    ids: list[str] = []
    with conn.cursor() as cur:
        for f in facts:
            cur.execute(
                """
                INSERT INTO ops.memory_facts (
                  fact_key, subject, predicate, object, fact_type,
                  importance, confidence, scope,
                  source_host, source_kind, source_ref, source_agent, evidence,
                  status, updated_at
                ) VALUES (
                  %(fact_key)s, %(subject)s, %(predicate)s, %(object)s, %(fact_type)s,
                  %(importance)s, %(confidence)s, %(scope)s,
                  %(source_host)s, %(source_kind)s, %(source_ref)s, %(source_agent)s, %(evidence)s,
                  'active', now()
                )
                ON CONFLICT (fact_key)
                DO UPDATE SET
                  subject = EXCLUDED.subject,
                  predicate = EXCLUDED.predicate,
                  object = EXCLUDED.object,
                  fact_type = EXCLUDED.fact_type,
                  importance = EXCLUDED.importance,
                  confidence = EXCLUDED.confidence,
                  scope = EXCLUDED.scope,
                  evidence = COALESCE(NULLIF(EXCLUDED.evidence, ''), ops.memory_facts.evidence),
                  source_kind = EXCLUDED.source_kind,
                  source_ref = COALESCE(EXCLUDED.source_ref, ops.memory_facts.source_ref),
                  source_agent = COALESCE(EXCLUDED.source_agent, ops.memory_facts.source_agent),
                  source_host = EXCLUDED.source_host,
                  status = 'active',
                  updated_at = now()
                RETURNING id::text
                """,
                {
                    **f,
                    "source_host": source_host,
                    "source_kind": source_kind,
                    "source_ref": source_ref,
                    "source_agent": source_agent,
                },
            )
            row = cur.fetchone()
            if row:
                ids.append(row[0])
    conn.commit()
    return ids


def insert_episodes(
    conn,
    episodes: list[dict],
    *,
    source_host: str,
    source_kind: str,
    source_ref: str | None,
    fact_ids: list[str],
) -> list[str]:
    ids: list[str] = []
    uuid_facts = fact_ids or []
    with conn.cursor() as cur:
        for e in episodes:
            cur.execute(
                """
                INSERT INTO ops.memory_episodes (
                  title, summary, outcome, result_state, importance, scope,
                  source_host, source_kind, source_ref, fact_ids, started_at
                ) VALUES (
                  %(title)s, %(summary)s, %(outcome)s, %(result_state)s, %(importance)s, %(scope)s,
                  %(source_host)s, %(source_kind)s, %(source_ref)s, %(fact_ids)s::uuid[], now()
                )
                RETURNING id::text
                """,
                {
                    **e,
                    "source_host": source_host,
                    "source_kind": source_kind,
                    "source_ref": source_ref,
                    "fact_ids": uuid_facts,
                },
            )
            row = cur.fetchone()
            if row:
                ids.append(row[0])
    conn.commit()
    return ids


def mirror_to_arcade(conn, fact_ids: list[str], episode_ids: list[str]) -> int:
    if not arcade or not fact_ids and not episode_ids:
        return 0
    n = 0
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if fact_ids:
            cur.execute(
                "SELECT * FROM ops.memory_facts WHERE id = ANY(%s::uuid[])",
                (fact_ids,),
            )
            for row in cur.fetchall():
                try:
                    arcade.mirror_memory_fact(dict(row))
                    n += 1
                except Exception as exc:
                    print(f"arcade fact warn: {exc}", file=sys.stderr)
        if episode_ids:
            cur.execute(
                "SELECT * FROM ops.memory_episodes WHERE id = ANY(%s::uuid[])",
                (episode_ids,),
            )
            for row in cur.fetchall():
                try:
                    arcade.mirror_memory_episode(dict(row))
                    n += 1
                except Exception as exc:
                    print(f"arcade episode warn: {exc}", file=sys.stderr)
    if fact_ids:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ops.memory_facts
                SET arcade_synced_at = now()
                WHERE id = ANY(%s::uuid[])
                """,
                (fact_ids,),
            )
        conn.commit()
    return n


def log_dream_run(conn, *, ok: bool, stats: dict, notes: str = "") -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ops.memory_dream_runs (stage, source_host, finished_at, ok, stats, notes)
            VALUES ('immediate', %s, now(), %s, %s::jsonb, %s)
            """,
            (
                env_get("CLAWSUM_SOURCE_HOST", "vps"),
                ok,
                json.dumps(stats),
                notes[:2000],
            ),
        )
    conn.commit()


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract memory facts into Postgres + Arcade")
    ap.add_argument("--text", default="")
    ap.add_argument("--file", default="")
    ap.add_argument("--source-kind", default="manual")
    ap.add_argument("--source-ref", default="")
    ap.add_argument("--source-agent", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-arcade", action="store_true")
    args = ap.parse_args()

    text = args.text
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8", errors="replace")
    if not text.strip() and not sys.stdin.isatty():
        text = sys.stdin.read()
    text = scrub(text)
    if not text:
        print("No input text", file=sys.stderr)
        return 2

    env = load_env()
    source_host = env_get("CLAWSUM_SOURCE_HOST", "vps")

    print("extracting…", flush=True)
    parsed = call_llm(env, text)
    facts = [f for f in (validate_fact(x) for x in (parsed.get("facts") or [])) if f]
    episodes = [e for e in (validate_episode(x) for x in (parsed.get("episodes") or [])) if e]

    out = {"facts": facts, "episodes": episodes, "source_host": source_host}
    if args.dry_run:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    conn = pg(env)
    try:
        fact_ids = upsert_facts(
            conn,
            facts,
            source_host=source_host,
            source_kind=args.source_kind,
            source_ref=args.source_ref or None,
            source_agent=args.source_agent or None,
        )
        episode_ids = insert_episodes(
            conn,
            episodes,
            source_host=source_host,
            source_kind=args.source_kind,
            source_ref=args.source_ref or None,
            fact_ids=fact_ids,
        )
        arcade_n = 0
        if not args.no_arcade:
            arcade_n = mirror_to_arcade(conn, fact_ids, episode_ids)
        stats = {
            "facts": len(fact_ids),
            "episodes": len(episode_ids),
            "arcade": arcade_n,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        log_dream_run(conn, ok=True, stats=stats, notes="memory-fact-extract")
        print(json.dumps({"ok": True, **stats, "fact_ids": fact_ids, "episode_ids": episode_ids}))
        return 0
    except Exception as exc:
        try:
            log_dream_run(conn, ok=False, stats={}, notes=str(exc)[:500])
        except Exception:
            pass
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
