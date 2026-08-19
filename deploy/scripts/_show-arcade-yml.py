#!/usr/bin/env python3
from pathlib import Path
t = Path("/docker/traefik/dynamic/clawsum-com.yml").read_text(encoding="utf-8")
i = t.find("arcade")
print("first arcade idx", i)
print("--- snippet ---")
print(t[max(0, i - 80) : i + 600])
print("--- count ---", t.count("arcade"))
