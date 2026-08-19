#!/usr/bin/env python3
from pathlib import Path

p = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/tui_dist/entry.js")
text = p.read_text(encoding="utf-8", errors="ignore")
i = text.find("const logoLines = logo(")
print(text[i : i + 1800])
print("\n\n==== logo function ====")
j = text.rfind("function logo(", 0, i)
print("fn at", j)
print(text[j : j + 1200] if j >= 0 else "not found")
print("\n\n==== CollapseToggle ====")
k = text.find("function CollapseToggle")
print(text[k : k + 800] if k >= 0 else "no fn")
