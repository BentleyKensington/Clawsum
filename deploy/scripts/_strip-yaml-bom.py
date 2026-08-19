#!/usr/bin/env python3
from pathlib import Path
import sys

for raw in sys.argv[1:]:
    p = Path(raw)
    b = p.read_bytes()
    if b.startswith(b"\xef\xbb\xbf"):
        p.write_bytes(b[3:])
        print("stripped", p)
    else:
        print("ok", p)
