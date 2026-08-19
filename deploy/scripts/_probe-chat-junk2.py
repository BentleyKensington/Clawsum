#!/usr/bin/env python3
from pathlib import Path

needles = (
    "Available tools",
    "availableTools",
    "Available Tools",
    "banner_logo",
    "banner_hero",
    "bannerLogo",
    "[bold #",
    "CLAWSUM HUD",
    "tool list",
    "Tools available",
)
roots = [
    Path("/paperclip/.hermes"),
    Path("/paperclip/.hermes-venv"),
    Path("/usr/local/lib/python3.12"),
    Path("/opt"),
]
for root in roots:
    if not root.exists():
        print("missing", root)
        continue
    print("scan", root)
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".js", ".mjs", ".css", ".html", ".json", ".py"}:
            continue
        try:
            if p.stat().st_size > 6_000_000:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        hits = [n for n in needles if n.lower() in text.lower()]
        if hits:
            print(f"  {p} :: {hits}")
