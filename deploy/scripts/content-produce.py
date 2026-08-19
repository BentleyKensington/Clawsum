#!/usr/bin/env python3
"""Render flyer card, first frame, thumbnail, and a short draft video via FFmpeg.

Does not publish. Writes under MEDIA_EXPORTS/content/<idea_id>/ and ops.content_assets.
"""
from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
EXPORTS = Path(os.environ.get("MEDIA_EXPORTS", "/docker/clawsum/data/media/exports"))
FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")


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
        raise RuntimeError((proc.stderr or proc.stdout or "psql fail")[-800])
    return [row.split("|") for row in proc.stdout.splitlines() if row.strip()]


def esc_drawtext(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def ffmpeg_card(out: Path, title: str, subtitle: str, w: int, h: int, seconds: float = 0.04) -> None:
    title = esc_drawtext(title[:80])
    subtitle = esc_drawtext(subtitle[:110])
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if not Path(font).is_file():
        font = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    font_arg = f":fontfile={font}" if Path(font).is_file() else ""
    filter_complex = (
        f"color=c=0x0b1220:s={w}x{h}:d={seconds},"
        f"drawbox=x=40:y=40:w=iw-80:h=ih-80:color=0xd4af37@0.9:t=4,"
        f"drawtext={font_arg}:text='{title}':fontsize={max(36, w // 18)}:"
        f"fontcolor=white:x=(w-text_w)/2:y=h*0.38:line_spacing=10,"
        f"drawtext={font_arg}:text='{subtitle}':fontsize={max(22, w // 32)}:"
        f"fontcolor=0xe8d5a3:x=(w-text_w)/2:y=h*0.55"
    )
    cmd = [
        FFMPEG,
        "-y",
        "-f",
        "lavfi",
        "-i",
        filter_complex,
        "-frames:v",
        "1",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-600:] or "ffmpeg card fail")


def ffmpeg_video(out: Path, title: str, hook: str) -> None:
    title = esc_drawtext(title[:70])
    hook = esc_drawtext(hook[:90])
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_arg = f":fontfile={font}" if Path(font).is_file() else ""
    # 9:16 Shorts draft ~8s, silent
    fc = (
        f"color=c=0x0b1220:s=1080x1920:d=8,"
        f"drawbox=x=48:y=80:w=iw-96:h=ih-160:color=0xd4af37@0.85:t=6,"
        f"drawtext={font_arg}:text='CLAWSUM':fontsize=42:fontcolor=0xd4af37:"
        f"x=(w-text_w)/2:y=160,"
        f"drawtext={font_arg}:text='{title}':fontsize=56:fontcolor=white:"
        f"x=(w-text_w)/2:y=h*0.40:line_spacing=12,"
        f"drawtext={font_arg}:text='{hook}':fontsize=36:fontcolor=0xe8d5a3:"
        f"x=(w-text_w)/2:y=h*0.58"
    )
    cmd = [
        FFMPEG,
        "-y",
        "-f",
        "lavfi",
        "-i",
        fc,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        "-t",
        "8",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-600:] or "ffmpeg video fail")


def record_asset(idea_id: str, pack_id: str | None, kind: str, path: Path) -> None:
    psql(
        """
        INSERT INTO ops.content_assets (id, idea_id, pack_id, kind, path, uri, meta)
        VALUES (%s, %s, %s, %s, %s, %s, '{}'::jsonb);
        """,
        str(uuid.uuid4()),
        idea_id,
        pack_id,
        kind,
        str(path),
        f"file://{path}",
    )


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--idea-id", required=True)
    args = ap.parse_args()
    idea_id = args.idea_id

    rows = psql(
        """
        SELECT i.title, COALESCE(p.hook, i.angle, ''), p.id
        FROM ops.content_ideas i
        LEFT JOIN LATERAL (
          SELECT id, hook FROM ops.content_packs
          WHERE idea_id = i.id ORDER BY created_at DESC LIMIT 1
        ) p ON true
        WHERE i.id = %s
        """,
        idea_id,
    )
    if not rows:
        raise SystemExit("idea not found")
    title, hook, pack_id = rows[0]
    pack_id = pack_id or None
    hook = hook or "Daily evergreen"

    out_dir = EXPORTS / "content" / idea_id
    out_dir.mkdir(parents=True, exist_ok=True)
    psql(
        "UPDATE ops.content_ideas SET status = 'producing', updated_at = now() WHERE id = %s",
        idea_id,
    )

    flyer = out_dir / "flyer.png"
    thumb = out_dir / "thumbnail.png"
    first = out_dir / "first-frame.png"
    video = out_dir / "draft-short.mp4"

    ffmpeg_card(flyer, title, hook, 1080, 1350)
    ffmpeg_card(thumb, title, hook, 1280, 720)
    ffmpeg_video(video, title, hook)
    # first frame from the rendered video
    proc = subprocess.run(
        [FFMPEG, "-y", "-i", str(video), "-frames:v", "1", str(first)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0 or not first.is_file():
        ffmpeg_card(first, title, hook, 1080, 1920)

    for kind, path in (
        ("flyer", flyer),
        ("thumbnail", thumb),
        ("first_frame", first),
        ("video", video),
    ):
        record_asset(idea_id, pack_id, kind, path)

    script_path = out_dir / "script.txt"
    if script_path.is_file():
        record_asset(idea_id, pack_id, "script", script_path)

    psql(
        "UPDATE ops.content_ideas SET status = 'ready', updated_at = now() WHERE id = %s",
        idea_id,
    )
    report = {
        "idea_id": idea_id,
        "title": title,
        "assets": {
            "flyer": str(flyer),
            "thumbnail": str(thumb),
            "first_frame": str(first),
            "video": str(video),
        },
    }
    (out_dir / "produce.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
