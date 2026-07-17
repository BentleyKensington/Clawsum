#!/usr/bin/env python3
import re
from pathlib import Path

def tok(path: Path) -> str | None:
    if not path.exists():
        return None
    m = re.search(r"^OPENCLAW_GATEWAY_TOKEN=(.*)$", path.read_text(), re.M)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'")

h = tok(Path("/docker/openclaw-qpr7/.env"))
c = tok(Path("/docker/clawsum/.env"))
print("hostinger_set", bool(h))
print("clawsum_set", bool(c))
if h and c:
    print("same_token", h == c)
