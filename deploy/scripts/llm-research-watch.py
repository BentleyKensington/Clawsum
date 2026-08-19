#!/usr/bin/env python3
"""Weekly / on-demand LLM + voice vendor watch.

  python3 llm-research-watch.py --now
Writes data/llm-lab/ and optional Obsidian note. No API keys required for the
public OpenRouter catalog fetch; Deepgram/NVIDIA sections are documentary if
keys are missing.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("America/Chicago")
except Exception:
    TZ = timezone(timedelta(hours=-5))
ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
OUT_DIR = ROOT / "data" / "llm-lab"
OBS = ROOT / "obsidian" / "LLM-Lab"


def fetch_openrouter_free(limit: int = 40) -> list[dict]:
    url = "https://openrouter.ai/api/v1/models"
    req = urllib.request.Request(url, headers={"User-Agent": "Clawsum-LLM-Lab/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
    except Exception as e:
        return [{"id": "error", "name": str(e)}]
    data = payload.get("data") or []
    free = []
    for m in data:
        pricing = m.get("pricing") or {}
        try:
            prompt = float(pricing.get("prompt") or 0)
            completion = float(pricing.get("completion") or 0)
        except (TypeError, ValueError):
            continue
        if prompt == 0 and completion == 0:
            free.append({"id": m.get("id"), "name": m.get("name")})
        if len(free) >= limit:
            break
    return free


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", action="store_true")
    args = ap.parse_args()
    _ = args
    now = datetime.now(TZ)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OBS.mkdir(parents=True, exist_ok=True)
    prev_path = OUT_DIR / "last-watch.json"
    prev = {}
    if prev_path.exists():
        try:
            prev = json.loads(prev_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}
    free = fetch_openrouter_free()
    prev_ids = {x.get("id") for x in prev.get("openrouter_free") or [] if x.get("id")}
    now_ids = {x.get("id") for x in free if x.get("id")}
    added = sorted(now_ids - prev_ids)
    dropped = sorted(prev_ids - now_ids)
    doc = {
        "ran_at": now.isoformat(),
        "openrouter_free": free,
        "added": added,
        "dropped": dropped,
        "notes": [
            "Deepgram: Flux STT /v2/listen for agents; Nova-3 for meetings; Flux TTS /v2/speak.",
            "NVIDIA: NIM OpenAI-compatible + OpenRouter nvidia/* :free slugs rotate.",
            "Clawsum policy: Codex interactive; mini/:free batch; escalate/llm:frontier for paid.",
            "Do not apply .env changes without Boss.",
        ],
    }
    prev_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    md = [
        f"# LLM Lab watch — {now.strftime('%Y-%m-%d %H:%M %Z')}",
        "",
        "## OpenRouter :free roster (prompt=0 and completion=0)",
        f"- Count this run: **{len(free)}** (capped sample)",
        f"- Added since last file: {', '.join(added) or 'none'}",
        f"- Dropped: {', '.join(dropped) or 'none'}",
        "",
        "### Sample ids",
    ]
    for row in free[:25]:
        md.append(f"- `{row.get('id')}`")
    md.extend(
        [
            "",
            "## Deepgram / NVIDIA (standing)",
            "- Re-read `docs/DEEPGRAM-AND-VOICE-STACK.md`.",
            "- Flux needs Ampere+ if self-hosting; VPS stays on hosted API.",
            "- Nemotron via OpenRouter `:free` when listed; NIM direct only if `NVIDIA_NIM_API_KEY` set.",
            "",
            "## Action",
            "Propose env slug updates on the LLM Lab Paperclip issue. Do not restart gateway.",
            "",
        ]
    )
    note = OBS / f"{now.strftime('%Y-%m-%d')}-watch.md"
    note.write_text("\n".join(md), encoding="utf-8")
    print(note)
    print(f"added={len(added)} dropped={len(dropped)} free_sample={len(free)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
