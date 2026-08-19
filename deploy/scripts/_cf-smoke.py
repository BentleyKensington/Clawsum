#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

ROOT = Path("/docker/clawsum")
cfg_path = ROOT / "data/.openclaw/openclaw.json"
cfg = json.loads(cfg_path.read_text())
agents = cfg.setdefault("agents", {}).setdefault("list", [])
want = {
    "content": {
        "id": "content",
        "name": "Content",
        "workspace": "/home/node/.openclaw/workspace-content",
        "tools": {"allow": ["read", "write", "edit", "exec"], "deny": []},
    },
    "social": {
        "id": "social",
        "name": "Social",
        "workspace": "/home/node/.openclaw/workspace-social",
        "tools": {"allow": ["read", "write", "edit"], "deny": ["exec"]},
    },
}
by = {a.get("id"): a for a in agents if isinstance(a, dict)}
for aid, entry in want.items():
    if aid in by:
        by[aid].update(entry)
        print("updated", aid)
    else:
        agents.append(entry)
        print("added", aid)
cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
for ws in ("content", "social"):
    d = ROOT / f"data/.openclaw/workspace-{ws}"
    d.mkdir(parents=True, exist_ok=True)
    soul = d / "SOUL.md"
    if not soul.is_file():
        soul.write_text(f"# {ws} — see docs/CONTENT-FACTORY.md\n", encoding="utf-8")

subprocess.run(["bash", str(ROOT / "scripts/install-content-factory-cron.sh")], check=False)
print(subprocess.check_output(["python3", str(ROOT / "scripts/content-factory.py"), "daily", "--count", "1"], text=True))
print(subprocess.check_output(["python3", str(ROOT / "scripts/content-factory.py"), "run-one"], text=True, timeout=180))
print("SMOKE_OK")
