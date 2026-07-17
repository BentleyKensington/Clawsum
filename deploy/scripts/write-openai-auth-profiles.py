#!/usr/bin/env python3
"""Write openai:default API key profile into every agent auth-profiles.json."""
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl

ROOT = Path("/docker/clawsum/data/.openclaw")
ENV = Path("/docker/clawsum/.env")

AGENTS = ghl.all_clawsum_openclaw_agent_ids()


def load_openai_key():
    text = ENV.read_text()
    m = re.search(r"^OPENAI_API_KEY=(.+)$", text, re.M)
    if not m:
        raise SystemExit("OPENAI_API_KEY missing in .env")
    return m.group(1).strip().strip('"').strip("'")


def update_agent(agent_id: str, api_key: str):
    auth_path = ROOT / "agents" / agent_id / "agent" / "auth-profiles.json"
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    if auth_path.exists():
        data = json.loads(auth_path.read_text())
    else:
        data = {"version": 1, "profiles": {}}
    profiles = data.setdefault("profiles", {})
    profiles["openai:default"] = {
        "provider": "openai",
        "type": "api_key",
        "key": api_key,
    }
    auth_path.write_text(json.dumps(data, indent=2) + "\n")
    auth_path.chmod(0o600)
    print(f"  {agent_id}: openai:default written")


def main():
    key = load_openai_key()
    if not key.startswith("sk-"):
        print("WARN: OPENAI_API_KEY does not look like sk-...")
    for agent_id in AGENTS:
        update_agent(agent_id, key)
    print("Done. For ChatGPT subscription (no API billing), run Codex OAuth once:")
    print("  ssh -t clawsum 'cd /docker/clawsum && docker compose run --rm openclaw-cli onboard --auth-choice openai-codex-device-code'")


if __name__ == "__main__":
    main()
