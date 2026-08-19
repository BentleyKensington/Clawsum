#!/usr/bin/env bash
set -euo pipefail
docker exec clawsum-paperclip-1 python3 - <<'PY'
from pathlib import Path
assets = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_dist/assets")
js = next(assets.glob("index-*.js"))
t = js.read_text(errors="ignore")
print("file", js)
for s in ["Hermes Agent", "agent_name", "get_branding", "display.skin"]:
    print(s, t.count(s))
idx = 0
n = 0
while n < 8:
    i = t.find("Hermes Agent", idx)
    if i < 0:
        break
    print(f"---{n}---", repr(t[max(0, i - 60) : i + 80]))
    idx = i + 1
    n += 1
print("HTML:")
print(Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_dist/index.html").read_text())
PY
