#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path("/docker/clawsum/data/.openclaw")
cfg = json.loads((ROOT / "openclaw.json").read_text())
defaults = cfg.get("agents", {}).get("defaults", {})
print("defaults.model:", defaults.get("model"))
print("codex plugin:", cfg.get("plugins", {}).get("entries", {}).get("codex"))
print("openai plugin:", cfg.get("plugins", {}).get("entries", {}).get("openai"))
print("auth:", json.dumps(cfg.get("auth", {}), indent=2)[:500])

agents = ROOT / "agents"
for agent_dir in sorted(agents.iterdir()):
    auth = agent_dir / "agent" / "auth-profiles.json"
    if auth.exists():
        data = json.loads(auth.read_text())
        profiles = data.get("profiles") or data
        names = list(profiles.keys()) if isinstance(profiles, dict) else []
        print(f"{agent_dir.name}: auth-profiles ({len(names)} profiles)")
    else:
        print(f"{agent_dir.name}: NO auth-profiles.json")
