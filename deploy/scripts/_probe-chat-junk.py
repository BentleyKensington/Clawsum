#!/usr/bin/env python3
"""Find Hermes chat welcome/tools/banner markup on the VPS."""
from pathlib import Path

needles = (
    "Available tools",
    "available tools",
    "banner_logo",
    "banner_hero",
    "[bold #",
    "CLAWSUM HUD",
    "tool-list",
    "AvailableTools",
)
roots = [
    Path("/paperclip/.hermes"),
    Path("/docker/clawsum/paperclip-data/.hermes"),
    Path("/usr/local/lib"),
]
seen = set()
for root in roots:
    if not root.exists():
        continue
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".js", ".mjs", ".tsx", ".ts", ".jsx", ".vue", ".css", ".html", ".json"}:
            continue
        if p.stat().st_size > 4_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        hits = [n for n in needles if n in text]
        if not hits:
            continue
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        print(f"{p} :: {hits}")
