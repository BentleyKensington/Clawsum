#!/usr/bin/env python3
"""Evergreen content factory — intake, research, pack, produce, queue.

Boss idea → Hermes files here → Research + Content pack → Media assets
→ Social queue (Tier 2 to post).

  python3 content-factory.py intake --text "idea..." [--source boss]
  python3 content-factory.py daily --count 1
  python3 content-factory.py pack --idea-id UUID
  python3 content-factory.py produce --idea-id UUID
  python3 content-factory.py queue --idea-id UUID [--when ISO|--now]
  python3 content-factory.py run-one   # next inbox/packed item through produce+queue
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import textwrap
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
EXPORTS = Path(os.environ.get("MEDIA_EXPORTS", "/docker/clawsum/data/media/exports"))
INBOX = Path(os.environ.get("MEDIA_INBOX", "/docker/clawsum/data/media/inbox"))

EVERGREEN_BANK = [
    {
        "title": "One decision that compounds for a decade",
        "angle": "Personal operating system — choose one lever, ignore noise",
        "niche": "ops-leadership",
    },
    {
        "title": "Why most dashboards lie to founders",
        "angle": "Measure leading indicators, not vanity counts",
        "niche": "ops-leadership",
    },
    {
        "title": "The 15-minute morning that protects the whole day",
        "angle": "Brief, approvals, one hard thing — then execute",
        "niche": "productivity",
    },
    {
        "title": "Agents don't replace judgment — they queue it",
        "angle": "Hermes proposes, specialists act, Boss decides Tier 2",
        "niche": "ai-ops",
    },
    {
        "title": "Evergreen content beats the news cycle",
        "angle": "Ship a useful idea every day that still works next year",
        "niche": "content",
    },
    {
        "title": "If it isn't written, it isn't a system",
        "angle": "SOUL, AUTHORITY, and Paperclip beat tribal knowledge",
        "niche": "ops-leadership",
    },
    {
        "title": "Stop asking for status. Build a pulse.",
        "angle": "Live board + show-your-work beats 'any update?'",
        "niche": "ops-leadership",
    },
]


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    p = ROOT / ".env"
    if p.is_file():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    env.update({k: v for k, v in os.environ.items() if v})
    return env


def psql(sql: str, *params: object) -> list[list[str]]:
    env = load_env()
    user = env.get("POSTGRES_USER", "clawsum")
    database = env.get("POSTGRES_DB", "clawsum")
    if params:
        lit = []
        for p in params:
            if p is None:
                lit.append("NULL")
            elif isinstance(p, bool):
                lit.append("TRUE" if p else "FALSE")
            elif isinstance(p, (int, float)):
                lit.append(str(p))
            else:
                s = str(p).replace("'", "''")
                lit.append(f"'{s}'")
        for litv in lit:
            sql = sql.replace("%s", litv, 1)
    sql = " ".join(sql.split())
    cmd = [
        "docker",
        "exec",
        "clawsum-postgres-1",
        "psql",
        "-U",
        user,
        "-d",
        database,
        "-t",
        "-A",
        "-F",
        "|",
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        sql,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        err = (proc.stderr or "") + (proc.stdout or "") or f"psql exit {proc.returncode}"
        raise RuntimeError(err[-800:])
    return [row.split("|") for row in proc.stdout.splitlines() if row.strip()]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(text: str, n: int = 40) -> str:
    keep = "".join(c.lower() if c.isalnum() else "-" for c in text)
    keep = "-".join(p for p in keep.split("-") if p)
    return (keep or "idea")[:n]


def build_pack(title: str, seed: str, angle: str, niche: str) -> dict:
    hook = angle or f"A sharper take on {title}"
    topic = title.strip()
    flyer = textwrap.dedent(
        f"""\
        {topic.upper()}

        {hook}

        Daily evergreen · Clawsum
        """
    ).strip()
    story = textwrap.dedent(
        f"""\
        Most people chase the news. This is the opposite.

        {topic}.

        {hook}.

        Save this if you want a system that still works next year —
        not a take that expires tonight.

        #evergreen #ops #clawsum
        """
    ).strip()
    script = textwrap.dedent(
        f"""\
        [0:00 HOOK — on-screen text + VO]
        {hook}

        [0:03 PROBLEM]
        Everyone is reacting. Feeds reset every hour. Nothing compounds.

        [0:08 INSIGHT]
        {topic}.
        {seed.strip()[:400] if seed else "Build one useful idea that still holds next year."}

        [0:18 PROOF / HOW]
        Write it. Assign it. Produce the asset. Queue the post.
        Hermes takes the idea. Research sharpens it. Media renders it. Social ships it.

        [0:26 CTA]
        Follow for one evergreen play a day. Comment TOPIC if you want tomorrow's angle on your niche.

        [END CARD]
        Clawsum · Daily evergreen
        """
    ).strip()
    prompts = [
        {
            "role": "flyer",
            "prompt": (
                f"Clean editorial flyer, dark navy background, gold accent line, "
                f"bold title '{topic}', subtitle '{hook}', generous whitespace, no logos of third parties"
            ),
        },
        {
            "role": "support_1",
            "prompt": f"Cinematic still, abstract control room / desk, '{niche or 'ops'}' mood, no text",
        },
        {
            "role": "support_2",
            "prompt": "First-frame energy: close crop of a founder at a screen, shallow depth, teal rim light",
        },
        {
            "role": "thumbnail",
            "prompt": (
                f"YouTube/Shorts thumbnail, high contrast, 3–5 words max: '{topic[:32]}', "
                "face or strong object left, text right, readable at mobile size"
            ),
        },
    ]
    seo = {
        "titles": [topic, f"{topic} (evergreen)", hook[:70]],
        "tags": ["evergreen", "ops", "clawsum", niche or "systems"],
        "description": story[:400],
    }
    return {
        "topic": topic,
        "hook": hook,
        "flyer_copy": flyer,
        "image_prompts": prompts,
        "social_story": story,
        "production_script": script,
        "seo": seo,
        "platforms": ["instagram", "youtube_shorts", "facebook"],
    }


def intake(text: str, source: str = "boss", evergreen: bool = True, niche: str = "") -> str:
    idea_id = str(uuid.uuid4())
    title = text.strip().splitlines()[0][:160] or "Untitled idea"
    psql(
        """
        INSERT INTO ops.content_ideas (
          id, source, title, seed_text, angle, evergreen, niche, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'inbox');
        """,
        idea_id,
        source,
        title,
        text.strip(),
        "",
        evergreen,
        niche or "general",
    )
    print(f"INTAKE {idea_id} {title}")
    return idea_id


def pick_evergreen() -> dict:
    # Prefer unused bank titles
    rows = psql("SELECT title FROM ops.content_ideas WHERE source = 'evergreen'")
    used = {r[0] for r in rows}
    for item in EVERGREEN_BANK:
        if item["title"] not in used:
            return item
    # rotate
    day = datetime.now(timezone.utc).timetuple().tm_yday
    return EVERGREEN_BANK[day % len(EVERGREEN_BANK)]


def daily(count: int = 1) -> list[str]:
    ids = []
    for _ in range(max(1, count)):
        item = pick_evergreen()
        ids.append(
            intake(
                f"{item['title']}\n\nAngle: {item['angle']}",
                source="evergreen",
                evergreen=True,
                niche=item.get("niche") or "general",
            )
        )
    return ids


def pack_idea(idea_id: str) -> str:
    rows = psql(
        "SELECT id, title, seed_text, angle, niche FROM ops.content_ideas WHERE id = %s",
        idea_id,
    )
    if not rows:
        raise SystemExit(f"idea not found: {idea_id}")
    _id, title, seed, angle, niche = rows[0]
    pack = build_pack(title, seed or "", angle or "", niche or "")
    pack_id = str(uuid.uuid4())
    psql(
        """
        INSERT INTO ops.content_packs (
          id, idea_id, topic, hook, flyer_copy, image_prompts, social_story,
          production_script, seo, platforms, pack_json
        ) VALUES (
          %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s::text[], %s::jsonb
        );
        UPDATE ops.content_ideas SET status = 'packed', updated_at = now(),
          angle = COALESCE(NULLIF(angle, ''), %s)
        WHERE id = %s;
        """,
        pack_id,
        idea_id,
        pack["topic"],
        pack["hook"],
        pack["flyer_copy"],
        json.dumps(pack["image_prompts"]),
        pack["social_story"],
        pack["production_script"],
        json.dumps(pack["seo"]),
        "{" + ",".join(pack["platforms"]) + "}",
        json.dumps(pack),
        pack["hook"],
        idea_id,
    )
    out_dir = EXPORTS / "content" / idea_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pack.json").write_text(json.dumps(pack, indent=2), encoding="utf-8")
    (out_dir / "script.txt").write_text(pack["production_script"], encoding="utf-8")
    (out_dir / "story.txt").write_text(pack["social_story"], encoding="utf-8")
    (out_dir / "flyer.txt").write_text(pack["flyer_copy"], encoding="utf-8")
    print(f"PACK {pack_id} → {out_dir}")
    return pack_id


def produce(idea_id: str) -> dict:
    script = ROOT / "scripts" / "content-produce.py"
    if not script.is_file():
        script = Path(__file__).resolve().parent / "content-produce.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--idea-id", idea_id],
        capture_output=True,
        text=True,
        timeout=180,
    )
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr[-500:], file=sys.stderr)
        raise SystemExit(proc.returncode)
    try:
        start = (proc.stdout or "").rfind("{")
        return json.loads(proc.stdout[start:]) if start >= 0 else {}
    except json.JSONDecodeError:
        return {}


def queue(idea_id: str, when: str | None, immediate: bool) -> None:
    rows = psql(
        """
        SELECT p.id, p.social_story, p.platforms
        FROM ops.content_packs p
        WHERE p.idea_id = %s
        ORDER BY p.created_at DESC LIMIT 1
        """,
        idea_id,
    )
    if not rows:
        raise SystemExit("pack first")
    pack_id, story, platforms = rows[0]
    plats = [p.strip() for p in platforms.strip("{}").split(",") if p.strip()] or [
        "instagram"
    ]
    if immediate:
        sched = datetime.now(timezone.utc)
        status = "pending_approval"
    elif when:
        sched = datetime.fromisoformat(when.replace("Z", "+00:00"))
        status = "pending_approval"
    else:
        # default: tomorrow 10:00 America/Chicago ≈ 15:00 UTC (approx; cron uses Chicago)
        sched = datetime.now(timezone.utc).replace(hour=15, minute=0, second=0, microsecond=0)
        if sched <= datetime.now(timezone.utc):
            sched = sched + timedelta(days=1)
        status = "pending_approval"
    for plat in plats:
        qid = str(uuid.uuid4())
        psql(
            """
            INSERT INTO ops.social_queue (
              id, idea_id, pack_id, platform, caption, scheduled_for, status
            ) VALUES (%s, %s, %s, %s, %s, %s::timestamptz, %s);
            """,
            qid,
            idea_id,
            pack_id,
            plat,
            story,
            sched.isoformat(),
            status,
        )
        print(f"QUEUE {qid} {plat} {status} {sched.isoformat()}")
    psql(
        "UPDATE ops.content_ideas SET status = 'queued', updated_at = now() WHERE id = %s",
        idea_id,
    )
    print(
        "NOTE: post/schedule is Tier 2 — Social agent waits for ops.approvals / Gerald "
        "unless Boss said 'post now' AND approval row is approved."
    )


def run_one() -> int:
    rows = psql(
        """
        SELECT id, status FROM ops.content_ideas
        WHERE status IN ('inbox', 'packed', 'producing')
        ORDER BY
          CASE status WHEN 'producing' THEN 0 WHEN 'packed' THEN 1 ELSE 2 END,
          created_at ASC
        LIMIT 1
        """
    )
    if not rows:
        print("NO_WORK")
        return 0
    idea_id, status = rows[0]
    print(f"RUN {idea_id} status={status}")
    if status == "inbox":
        pack_idea(idea_id)
        status = "packed"
    if status in ("packed", "producing"):
        produce(idea_id)
    queue(idea_id, when=None, immediate=False)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Clawsum evergreen content factory")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_in = sub.add_parser("intake")
    p_in.add_argument("--text", required=True)
    p_in.add_argument("--source", default="boss", choices=["boss", "trend", "evergreen", "agent"])
    p_in.add_argument("--niche", default="")
    p_in.add_argument("--not-evergreen", action="store_true")

    p_d = sub.add_parser("daily")
    p_d.add_argument("--count", type=int, default=1)

    p_p = sub.add_parser("pack")
    p_p.add_argument("--idea-id", required=True)

    p_pr = sub.add_parser("produce")
    p_pr.add_argument("--idea-id", required=True)

    p_q = sub.add_parser("queue")
    p_q.add_argument("--idea-id", required=True)
    p_q.add_argument("--when", default=None, help="ISO schedule time")
    p_q.add_argument("--now", action="store_true", help="Immediate (still Tier 2 approval)")

    sub.add_parser("run-one")

    args = ap.parse_args()
    if args.cmd == "intake":
        intake(args.text, source=args.source, evergreen=not args.not_evergreen, niche=args.niche)
    elif args.cmd == "daily":
        daily(args.count)
    elif args.cmd == "pack":
        pack_idea(args.idea_id)
    elif args.cmd == "produce":
        produce(args.idea_id)
    elif args.cmd == "queue":
        queue(args.idea_id, args.when, args.now)
    elif args.cmd == "run-one":
        return run_one()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
