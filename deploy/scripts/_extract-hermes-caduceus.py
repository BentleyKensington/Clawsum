#!/usr/bin/env python3
from pathlib import Path

p = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/banner.py")
t = p.read_text(encoding="utf-8", errors="ignore") if p.is_file() else ""
print("banner.py exists", p.is_file(), "len", len(t))
for n in ["caduceus", "HERMES", "logo", "DEFAULT", "staff"]:
    print(n, t.lower().count(n.lower()) if t else 0)
if t:
    print(t[:2500])
    print("---TAIL---")
    print(t[-1500:])
