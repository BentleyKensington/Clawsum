#!/usr/bin/env python3
import json
import urllib.request
from pathlib import Path

raw = urllib.request.urlopen("http://127.0.0.1:9119/api/dashboard/plugins", timeout=8).read()
data = json.loads(raw)
print("plugins:")
for p in data:
    tab = p.get("tab") or {}
    print(
        f"  {p.get('name')}: label={p.get('label')} path={tab.get('path')} override={tab.get('override')} ver={p.get('version')}"
    )

idx = Path("/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js")
# host bind mount
for p in (
    Path("/docker/clawsum/paperclip-data/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js"),
    Path("/docker/clawsum/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/index.js"),
):
    if p.is_file():
        text = p.read_text(errors="replace")
        print(p, "HUD 1.4.1" in text, "bytes", p.stat().st_size)
