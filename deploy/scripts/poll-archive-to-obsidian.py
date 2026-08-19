#!/usr/bin/env python3
"""
Poll ChatGPT archive + memory facts → Obsidian Admin/Archive + Admin/Memory.

Does not dump personal chats. Incremental via a marker of last poll time.

Usage:
  python3 poll-archive-to-obsidian.py
  python3 poll-archive-to-obsidian.py --since 2026-08-01
  python3 poll-archive-to-obsidian.py --promote   # also run promote-archive-to-memory
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Need psycopg2", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
ENV_FILE = ROOT / ".env"
OBS = ROOT / "obsidian"
ARCHIVE_DIR = OBS / "Admin" / "Archive"
MEMORY_DIR = OBS / "Admin" / "Memory"
MARKER = ROOT / "data" / "reports" / ".archive-obsidian-poll.json"


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            k, _, v = raw.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    out.update({k: v for k, v in os.environ.items() if v})
    return out


def connect(env: dict):
    return psycopg2.connect(
        host=env.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(env.get("POSTGRES_PORT", "5432") or "5432"),
        user=env.get("POSTGRES_USER", "clawsum"),
        password=env.get("POSTGRES_PASSWORD", ""),
        dbname=env.get("POSTGRES_DB", "clawsum"),
    )


def last_poll() -> str | None:
    if not MARKER.exists():
        return None
    try:
        return json.loads(MARKER.read_text()).get("last_poll")
    except Exception:
        return None


def save_poll(iso: str, stats: dict) -> None:
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(json.dumps({"last_poll": iso, **stats}, indent=2) + "\n")


def write_md(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    try:
        os.chmod(path, 0o644)
    except OSError:
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="ISO timestamp; default = last poll or 7 days")
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--promote", action="store_true", help="Run promote-archive-to-memory first")
    args = ap.parse_args()

    env = load_env()
    if args.promote:
        promo = Path(__file__).resolve().parent / "promote-archive-to-memory.py"
        if promo.is_file():
            print("promote-archive-to-memory…", flush=True)
            subprocess.call([sys.executable, str(promo), "--resume", "--limit", "40"])

    since = args.since or last_poll()
    conn = connect(env)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    params: list = []
    where = "COALESCE(c.scope, 'unknown') <> 'personal'"
    if since:
        where += " AND COALESCE(c.updated_at_source, c.updated_at) > %s::timestamptz"
        params.append(since)

    cur.execute(
        f"""
        SELECT c.id::text, c.title, c.scope, c.work_status,
               COALESCE(c.intent_summary, c.summary, '') AS blurb,
               c.topics, c.updated_at_source, c.approved_for_hermes
        FROM ops.conversations c
        WHERE {where}
        ORDER BY COALESCE(c.updated_at_source, c.updated_at) DESC NULLS LAST
        LIMIT %s
        """,
        tuple(params + [args.limit]),
    )
    convos = [dict(r) for r in cur.fetchall()]

    cur.execute(
        """
        SELECT subject, predicate, object, fact_type, importance, updated_at
        FROM ops.memory_facts
        WHERE status = 'active'
          AND COALESCE(scope, 'business') <> 'personal'
          AND source_kind IN ('chatgpt', 'dream', 'manual')
        ORDER BY updated_at DESC
        LIMIT 40
        """
    )
    facts = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()

    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    lines = [
        f"# ChatGPT archive pulse — {day}",
        "",
        f"Polled {now.isoformat()} · skipped personal · {len(convos)} conversation(s), {len(facts)} recent facts.",
        "",
        "Source of truth stays Postgres (`ops.conversations`, `ops.memory_facts`). This note is the readable digest.",
        "",
        "## Conversations to remember",
        "",
    ]
    if not convos:
        lines.append("_Nothing new since last poll._")
    for c in convos:
        title = c.get("title") or "(untitled)"
        blurb = (c.get("blurb") or "").replace("\n", " ").strip()[:280]
        topics = c.get("topics") or []
        topic_s = ", ".join(topics[:6]) if isinstance(topics, list) else ""
        lines.append(
            f"- **{title}** — {c.get('scope')}/{c.get('work_status')}"
            + (f" · {topic_s}" if topic_s else "")
        )
        if blurb:
            lines.append(f"  - {blurb}")

    lines += ["", "## Facts worth keeping in mind", ""]
    if not facts:
        lines.append("_No recent non-personal memory facts._")
    for f in facts[:25]:
        lines.append(
            f"- **{f.get('subject')}** {f.get('predicate')} {f.get('object')} "
            f"({f.get('importance') or 'medium'})"
        )

    lines += [
        "",
        "## How this updates memory",
        "",
        "1. This file + `Admin/Memory/from-chatgpt-archive.md` (rolling).",
        "2. Nightly dream compresses `ops.memory_facts` into `Admin/Memory/*-dream.md`.",
        "3. Re-import a new ChatGPT export anytime, then this poller picks up deltas.",
        "",
    ]
    body = "\n".join(lines) + "\n"
    pulse = ARCHIVE_DIR / f"{day}-archive-pulse.md"
    latest = ARCHIVE_DIR / "Latest-Archive-Pulse.md"
    rolling = MEMORY_DIR / "from-chatgpt-archive.md"
    write_md(pulse, body)
    write_md(latest, f"# Latest archive pulse\n\nSee [[{pulse.stem}]]\n\n" + body)
    write_md(rolling, body)
    pointer = OBS / "Admin" / "Latest-Archive.md"
    write_md(pointer, "# Latest ChatGPT archive pulse\n\nSee [[Admin/Archive/Latest-Archive-Pulse]]\n")

    try:
        os.system(f"chown -R 1000:1000 {ARCHIVE_DIR} {MEMORY_DIR} {pointer} 2>/dev/null")
    except Exception:
        pass

    stats = {"conversations": len(convos), "facts": len(facts), "pulse": str(pulse)}
    save_poll(now.isoformat(), stats)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
