#!/usr/bin/env python3
from pathlib import Path

files = [
    Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/tui_dist/entry.js"),
    Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_dist/assets/index-WrAtZQWO.js"),
]
needles = ["Available tools", "bannerLogo", "banner_logo", "banner_hero", "Available Tools"]
for p in files:
    if not p.is_file():
        print("missing", p)
        continue
    text = p.read_text(encoding="utf-8", errors="ignore")
    print("=" * 80)
    print(p, "len", len(text))
    for n in needles:
        idx = 0
        found = 0
        while found < 3:
            i = text.find(n, idx)
            if i < 0:
                break
            found += 1
            a = max(0, i - 220)
            b = min(len(text), i + 280)
            print(f"\n--- {n} @{i} ---\n{text[a:b]}\n")
            idx = i + len(n)
