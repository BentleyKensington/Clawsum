#!/usr/bin/env python3
import json
from pathlib import Path

p = Path("/docker/clawsum/paperclip-data/instances/default/config.json")
c = json.loads(p.read_text())
c.setdefault("server", {})
c["server"]["host"] = "127.0.0.1"
c["server"]["bind"] = "loopback"
c["server"]["port"] = 3100
c["server"]["deploymentMode"] = "local_trusted"
p.write_text(json.dumps(c, indent=2) + "\n")
print("patched loopback", p)
