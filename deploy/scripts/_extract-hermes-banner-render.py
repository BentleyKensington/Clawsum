#!/usr/bin/env python3
from pathlib import Path

p = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/tui_dist/entry.js")
text = p.read_text(encoding="utf-8", errors="ignore")
for n in [
    "bannerLogo",
    "theme.bannerLogo",
    "bannerHero",
    "Available Tools",
    "toolsOpen",
    "toolsBody",
    "CollapseToggle",
    "welcome banner",
    "Banner",
]:
    print("\n#####", n, "count", text.count(n))

# find render of banner logo near JSX
idx = 0
hits = 0
while hits < 8:
    i = text.find("bannerLogo", idx)
    if i < 0:
        break
    hits += 1
    print(f"\n=== bannerLogo @{i} ===\n{text[max(0,i-160):i+220]}\n")
    idx = i + 10

i = text.find('title: "Available Tools"')
print("\n=== Available Tools block ===\n", text[max(0, i - 800) : i + 900])
