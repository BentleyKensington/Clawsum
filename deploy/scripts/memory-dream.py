#!/usr/bin/env python3
"""
Phase 2 memory dreaming — staged consolidation.

Stages:
  hourly   — expire temporary, merge near-dupes, resolve simple contradictions
  nightly  — hourly + LLM compression for hot subjects + Obsidian dream note
  weekly   — preference/procedure abstractions + Self-Model touch-up

Usage (VPS):
  python3 memory-dream.py --stage hourly
  python3 memory-dream.py --stage nightly
  python3 memory-dream.py --stage weekly
  python3 memory-dream.py --stage nightly --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Need psycopg2", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
SCRIPT_DIR = Path(__file__).resolve().parent
OBSIDIAN_MEMORY = ROOT / "obsidian" / "Admin" / "Memory"
OBSIDIAN_SELF = ROOT / "obsidian" / "Admin" / "Self-Model.md"

sys.path.insert(0, str(SCRIPT_DIR))
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
upsert_facts = _mfe.upsert_facts
http_json = _mfe.http_json
openrouter_api_key = _mfe.openrouter_api_key
openrouter_enabled = _mfe.openrouter_enabled
norm_key = _mfe.norm_key

try:
    import clawsum_arcade as arcade
except Exception:
    arcade = None  # type: ignore

CONF_RANK = {
    "confirmed": 5,
    "user_stated": 4,
    "observed": 3,
    "inferred": 2,
    "guessed": 1,
}
IMP_RANK = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "temporary": 1,
}

# Predicates where conflicting objects usually mean "current vs historical"
EXCLUSIVE_PREDICATES = {
    "owns",
    "has",
    "using",
    "uses",
    "current",
    "prefers",
    "preference",
    "lives_in",
    "primary",
    "running",
    "deployed_on",
}

NIGHTLY_SYSTEM = """You consolidate memory facts for a personal AI ops platform (dreaming).
Given facts for ONE subject, return ONLY JSON:
{
  "keep_ids": ["uuid", ...],
  "historize_ids": ["uuid", ...],
  "merged_facts": [
    {
      "subject": "...",
      "predicate": "...",
      "object": "...",
      "fact_type": "preference|ownership|project|attribute|observation|goal|relationship|task|problem",
      "importance": "critical|high|medium|low|temporary",
      "confidence": "confirmed|user_stated|observed|inferred",
      "scope": "business|mixed|personal",
      "evidence": "compressed from dreaming"
    }
  ],
  "notes": "one short sentence on what changed"
}

Rules:
- Prefer fewer, stronger facts over many near-duplicates.
- If GPU/hardware ownership changed over time, keep current as active; historize older.
- Merge synonymous preferences into one strong preference.
- NEVER invent secrets or credentials.
- historize_ids must be subset of provided ids; keep_ids the rest you still want active.
- Max 8 merged_facts. Empty merged_facts OK if only historizing dupes.
"""


def fact_score(row: dict) -> tuple:
    return (
        CONF_RANK.get(str(row.get("confidence") or ""), 0),
        IMP_RANK.get(str(row.get("importance") or ""), 0),
        row.get("updated_at") or datetime.min.replace(tzinfo=timezone.utc),
    )


def norm_obj(text: str) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"[^\w\s\-+./]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def load_active_facts(conn, *, limit: int = 0) -> list[dict]:
    sql = """
        SELECT id::text AS id, fact_key, subject, predicate, object, fact_type,
               importance, confidence, scope, status, source_kind, source_ref,
               evidence, valid_to, updated_at, created_at, superseded_by::text AS superseded_by
        FROM ops.memory_facts
        WHERE status = 'active'
        ORDER BY updated_at DESC
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


def historize(conn, loser_id: str, winner_id: str | None, *, dry_run: bool) -> None:
    if dry_run:
        return
    with conn.cursor() as cur:
        if winner_id:
            cur.execute(
                """
                UPDATE ops.memory_facts
                SET status = 'historical',
                    superseded_by = %s::uuid,
                    updated_at = now()
                WHERE id = %s::uuid AND status = 'active'
                """,
                (winner_id, loser_id),
            )
        else:
            cur.execute(
                """
                UPDATE ops.memory_facts
                SET status = 'historical', updated_at = now()
                WHERE id = %s::uuid AND status = 'active'
                """,
                (loser_id,),
            )
    conn.commit()
    if arcade and winner_id:
        try:
            arcade.link_supersedes(winner_id, loser_id)
        except Exception:
            pass


def expire_temporary(conn, *, dry_run: bool) -> int:
    with conn.cursor() as cur:
        if dry_run:
            cur.execute(
                """
                SELECT count(*) FROM ops.memory_facts
                WHERE status = 'active' AND importance = 'temporary'
                  AND valid_to IS NOT NULL AND valid_to < now()
                """
            )
            return int(cur.fetchone()[0])
        cur.execute(
            """
            UPDATE ops.memory_facts
            SET status = 'historical', updated_at = now()
            WHERE status = 'active' AND importance = 'temporary'
              AND valid_to IS NOT NULL AND valid_to < now()
            """
        )
        n = cur.rowcount
    conn.commit()
    return n


def merge_near_dupes(conn, facts: list[dict], *, dry_run: bool) -> int:
    """Same subject+predicate+normalized object → keep best, historize rest."""
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for f in facts:
        key = (
            (f.get("subject") or "").strip().lower(),
            (f.get("predicate") or "").strip().lower(),
            norm_obj(f.get("object") or ""),
        )
        if not key[0] or not key[1] or not key[2]:
            continue
        groups[key].append(f)

    merged = 0
    for _key, rows in groups.items():
        if len(rows) < 2:
            continue
        rows.sort(key=fact_score, reverse=True)
        winner = rows[0]
        for loser in rows[1:]:
            historize(conn, loser["id"], winner["id"], dry_run=dry_run)
            merged += 1
    return merged


def resolve_exclusive_conflicts(conn, facts: list[dict], *, dry_run: bool) -> int:
    """Same subject + exclusive predicate, different objects → newer/higher wins."""
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for f in facts:
        pred = (f.get("predicate") or "").strip().lower()
        if pred not in EXCLUSIVE_PREDICATES:
            continue
        subj = (f.get("subject") or "").strip().lower()
        if not subj:
            continue
        groups[(subj, pred)].append(f)

    n = 0
    for _key, rows in groups.items():
        # Distinct normalized objects
        by_obj: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            by_obj[norm_obj(r.get("object") or "")].append(r)
        if len(by_obj) < 2:
            continue
        # Pick overall winner, historize other object clusters' best (all of them)
        flat = sorted(rows, key=fact_score, reverse=True)
        winner = flat[0]
        win_obj = norm_obj(winner.get("object") or "")
        for obj, cluster in by_obj.items():
            if obj == win_obj:
                continue
            cluster.sort(key=fact_score, reverse=True)
            for loser in cluster:
                historize(conn, loser["id"], winner["id"], dry_run=dry_run)
                n += 1
    return n


def bump_agreement_confidence(conn, facts: list[dict], *, dry_run: bool) -> int:
    """If ≥2 independent sources share near-same fact, bump winner toward observed/confirmed."""
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for f in facts:
        key = (
            (f.get("subject") or "").strip().lower(),
            (f.get("predicate") or "").strip().lower(),
            norm_obj(f.get("object") or ""),
        )
        if key[2]:
            groups[key].append(f)
    bumped = 0
    for _key, rows in groups.items():
        sources = {(r.get("source_kind"), r.get("source_ref")) for r in rows}
        if len(sources) < 2:
            continue
        rows.sort(key=fact_score, reverse=True)
        winner = rows[0]
        cur_conf = winner.get("confidence") or "inferred"
        if CONF_RANK.get(cur_conf, 0) >= CONF_RANK["observed"]:
            continue
        if dry_run:
            bumped += 1
            continue
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ops.memory_facts
                SET confidence = 'observed', updated_at = now()
                WHERE id = %s::uuid AND status = 'active'
                """,
                (winner["id"],),
            )
        conn.commit()
        bumped += 1
    return bumped


def call_dream_llm(env: dict, subject: str, facts: list[dict]) -> dict[str, Any]:
    slim = [
        {
            "id": f["id"],
            "predicate": f["predicate"],
            "object": f["object"],
            "importance": f["importance"],
            "confidence": f["confidence"],
            "scope": f["scope"],
            "updated_at": str(f.get("updated_at") or ""),
        }
        for f in facts[:40]
    ]
    user = json.dumps({"subject": subject, "facts": slim}, ensure_ascii=False)
    openai_key = (env.get("OPENAI_API_KEY") or "").strip()
    model = (env.get("MEMORY_DREAM_MODEL") or env.get("MEMORY_EXTRACT_MODEL") or "").strip()

    if openai_key:
        model = model or "gpt-4.1-mini"
        data = http_json(
            "https://api.openai.com/v1/chat/completions",
            {
                "model": model.replace("openai/", ""),
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": NIGHTLY_SYSTEM},
                    {"role": "user", "content": user[:60000]},
                ],
            },
            {"Authorization": f"Bearer {openai_key}"},
            timeout=120,
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
                    {"role": "system", "content": NIGHTLY_SYSTEM},
                    {"role": "user", "content": user[:60000]},
                ],
            },
            {
                "Authorization": f"Bearer {openrouter_api_key()}",
                "HTTP-Referer": "https://clawsum.com",
                "X-Title": "Clawsum Memory Dream",
            },
            timeout=120,
        )
    else:
        raise RuntimeError("Need OPENAI_API_KEY or OPENROUTER_API_KEY for nightly dream")

    content = (
        ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    ).strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise RuntimeError("dream JSON root must be object")
    return parsed


def nightly_llm_compress(
    conn,
    env: dict,
    facts: list[dict],
    *,
    dry_run: bool,
    max_subjects: int,
    sleep_s: float,
) -> dict[str, int]:
    by_subj: dict[str, list[dict]] = defaultdict(list)
    for f in facts:
        subj = (f.get("subject") or "").strip()
        if subj:
            by_subj[subj].append(f)

    hot = sorted(by_subj.items(), key=lambda kv: -len(kv[1]))
    hot = [(s, rows) for s, rows in hot if len(rows) >= 4][:max_subjects]

    stats = {"subjects": 0, "historized": 0, "merged_upserts": 0, "llm_fail": 0}
    source_host = env_get("CLAWSUM_SOURCE_HOST", "vps")

    for subject, rows in hot:
        stats["subjects"] += 1
        try:
            parsed = call_dream_llm(env, subject, rows)
        except Exception as exc:
            stats["llm_fail"] += 1
            print(f"dream llm fail [{subject}]: {exc}", file=sys.stderr, flush=True)
            time.sleep(max(sleep_s, 1.0))
            continue

        id_set = {r["id"] for r in rows}
        for hid in parsed.get("historize_ids") or []:
            hid = str(hid)
            if hid not in id_set:
                continue
            # Prefer first keep_id as winner if present
            winner = None
            keeps = [str(x) for x in (parsed.get("keep_ids") or []) if str(x) in id_set]
            if keeps:
                winner = keeps[0]
            historize(conn, hid, winner, dry_run=dry_run)
            stats["historized"] += 1

        merged = []
        for raw in parsed.get("merged_facts") or []:
            f = validate_fact(raw)
            if not f or f.get("scope") == "personal":
                continue
            if f["scope"] not in ("business", "mixed", "unknown"):
                f["scope"] = "business"
            # Prefer confirmed after dream compression
            if f["confidence"] in ("inferred", "guessed"):
                f["confidence"] = "observed"
            merged.append(f)

        if merged and not dry_run:
            ids = upsert_facts(
                conn,
                merged,
                source_host=source_host,
                source_kind="dream",
                source_ref=f"nightly:{datetime.now(timezone.utc).strftime('%Y%m%d')}:{subject[:40]}",
                source_agent="memory-dream",
            )
            stats["merged_upserts"] += len(ids)
            if arcade:
                try:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute(
                            "SELECT * FROM ops.memory_facts WHERE id = ANY(%s::uuid[])",
                            (ids,),
                        )
                        for row in cur.fetchall():
                            arcade.mirror_memory_fact(dict(row))
                except Exception as exc:
                    print(f"arcade warn: {exc}", file=sys.stderr)

        note = (parsed.get("notes") or "").strip()
        if note:
            print(f"  [{subject}] {note}", flush=True)
        time.sleep(sleep_s)

    return stats


def write_obsidian_dream(stats: dict, sample_facts: list[dict], *, stage: str) -> Path | None:
    OBSIDIAN_MEMORY.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if stage == "weekly":
        path = OBSIDIAN_MEMORY / f"weekly-{datetime.now(timezone.utc).strftime('%Y-W%W')}.md"
        title = f"Weekly memory dream — {day}"
    else:
        path = OBSIDIAN_MEMORY / f"{day}-dream.md"
        title = f"Nightly memory dream — {day}"

    lines = [
        f"# {title}",
        "",
        f"_Generated {datetime.now(timezone.utc).isoformat()} · stage=`{stage}`_",
        "",
        "## Stats",
        "",
        "```json",
        json.dumps(stats, indent=2, default=str),
        "```",
        "",
        "## Sample active facts",
        "",
    ]
    for f in sample_facts[:25]:
        lines.append(
            f"- **{f.get('subject')}** `{f.get('predicate')}` {f.get('object')} "
            f"_( {f.get('importance')}/{f.get('confidence')} )_"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Personal-scope facts are never promoted here.",
            "- Historical facts remain queryable but are not treated as current.",
            "- Next: Hermes retrieval should prefer `status=active` + higher confidence.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")

    latest = ROOT / "obsidian" / "Admin" / "Latest-Dream.md"
    try:
        latest.write_text(
            f"# Latest dream\n\nSee [[{path.relative_to(ROOT / 'obsidian').as_posix().replace('.md','')}]]\n",
            encoding="utf-8",
        )
    except Exception:
        latest.write_text(f"# Latest dream\n\nSee `{path.name}`\n", encoding="utf-8")

    # Best-effort ownership for Obsidian UID
    try:
        os.chown(path, 1000, 1000)
        os.chown(latest, 1000, 1000)
        os.chown(OBSIDIAN_MEMORY, 1000, 1000)
    except Exception:
        pass
    return path


def touch_self_model(stats: dict) -> None:
    OBSIDIAN_SELF.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    block = (
        f"\n## Dream update {stamp}\n\n"
        f"- Active facts consolidated (see Admin/Memory).\n"
        f"- Dream stats: `{json.dumps(stats, default=str)[:500]}`\n"
    )
    if OBSIDIAN_SELF.exists():
        text = OBSIDIAN_SELF.read_text(encoding="utf-8", errors="replace")
        if f"## Dream update {stamp}" in text:
            return
        OBSIDIAN_SELF.write_text(text.rstrip() + "\n" + block, encoding="utf-8")
    else:
        OBSIDIAN_SELF.write_text(
            "# Clawsum Self-Model\n\nLiving summary of Boss preferences, stack, and projects.\n"
            + block,
            encoding="utf-8",
        )
    try:
        os.chown(OBSIDIAN_SELF, 1000, 1000)
    except Exception:
        pass


def log_run(conn, stage: str, ok: bool, stats: dict, notes: str = "") -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ops.memory_dream_runs (stage, source_host, finished_at, ok, stats, notes)
            VALUES (%s, %s, now(), %s, %s::jsonb, %s)
            """,
            (
                stage,
                env_get("CLAWSUM_SOURCE_HOST", "vps"),
                ok,
                json.dumps(stats, default=str),
                notes[:2000],
            ),
        )
    conn.commit()


def run_hourly(conn, *, dry_run: bool) -> dict:
    facts = load_active_facts(conn)
    stats = {
        "active_before": len(facts),
        "expired_temporary": expire_temporary(conn, dry_run=dry_run),
        "near_dupes_merged": 0,
        "exclusive_conflicts": 0,
        "confidence_bumps": 0,
    }
    # Reload after expire
    facts = load_active_facts(conn) if not dry_run else facts
    stats["near_dupes_merged"] = merge_near_dupes(conn, facts, dry_run=dry_run)
    facts = load_active_facts(conn) if not dry_run else facts
    stats["exclusive_conflicts"] = resolve_exclusive_conflicts(conn, facts, dry_run=dry_run)
    facts = load_active_facts(conn) if not dry_run else facts
    stats["confidence_bumps"] = bump_agreement_confidence(conn, facts, dry_run=dry_run)
    facts_after = load_active_facts(conn)
    stats["active_after"] = len(facts_after)
    return stats


def run_nightly(conn, env: dict, *, dry_run: bool, max_subjects: int, sleep_s: float) -> dict:
    stats = {"hourly": run_hourly(conn, dry_run=dry_run)}
    facts = load_active_facts(conn)
    llm = nightly_llm_compress(
        conn,
        env,
        facts,
        dry_run=dry_run,
        max_subjects=max_subjects,
        sleep_s=sleep_s,
    )
    stats["llm"] = llm
    facts = load_active_facts(conn)
    stats["active_after"] = len(facts)
    if not dry_run:
        path = write_obsidian_dream(stats, facts[:40], stage="nightly")
        stats["obsidian"] = str(path) if path else None
    return stats


def run_weekly(conn, env: dict, *, dry_run: bool, max_subjects: int, sleep_s: float) -> dict:
    # Weekly = deeper nightly + self-model
    stats = run_nightly(
        conn, env, dry_run=dry_run, max_subjects=max(max_subjects, 40), sleep_s=sleep_s
    )
    facts = load_active_facts(conn)
    # Preference rollup heuristic
    prefs = [
        f
        for f in facts
        if (f.get("predicate") or "").lower() in ("prefers", "preference", "avoids", "likes")
        and f.get("importance") in ("critical", "high", "medium")
    ]
    stats["preference_facts"] = len(prefs)
    if not dry_run:
        path = write_obsidian_dream(stats, prefs[:30] or facts[:30], stage="weekly")
        stats["obsidian_weekly"] = str(path) if path else None
        touch_self_model({"preferences": len(prefs), "active_facts": len(facts)})
        stats["self_model"] = str(OBSIDIAN_SELF)
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=("hourly", "nightly", "weekly"), required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-subjects", type=int, default=25)
    ap.add_argument("--sleep", type=float, default=0.35)
    args = ap.parse_args()

    env = load_env()
    conn = pg(env)
    ok = True
    try:
        if args.stage == "hourly":
            stats = run_hourly(conn, dry_run=args.dry_run)
        elif args.stage == "nightly":
            stats = run_nightly(
                conn,
                env,
                dry_run=args.dry_run,
                max_subjects=args.max_subjects,
                sleep_s=args.sleep,
            )
        else:
            stats = run_weekly(
                conn,
                env,
                dry_run=args.dry_run,
                max_subjects=args.max_subjects,
                sleep_s=args.sleep,
            )
        log_run(conn, args.stage, True, stats, notes=f"memory-dream dry_run={args.dry_run}")
        print(json.dumps({"ok": True, "stage": args.stage, "dry_run": args.dry_run, **stats}, default=str))
        return 0
    except Exception as exc:
        ok = False
        try:
            log_run(conn, args.stage, False, {}, notes=str(exc)[:500])
        except Exception:
            pass
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
        if not ok:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
