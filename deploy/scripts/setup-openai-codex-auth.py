#!/usr/bin/env python3
"""Enable Codex plugin and propagate OAuth auth profiles to all agents."""
import json
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl

ROOT = Path("/docker/clawsum/data/.openclaw")
CONFIG = ROOT / "openclaw.json"
SOURCE_AUTH = ROOT / "agents/main/agent/auth-profiles.json"
SOURCE_CODEX = ROOT / "agents/main/agent/codex-home"

AGENT_IDS = ghl.all_clawsum_openclaw_agent_ids()


def main():
    cfg = json.loads(CONFIG.read_text())

    plugins = cfg.setdefault("plugins", {})
    entries = plugins.setdefault("entries", {})
    entries["codex"] = {"enabled": True}
    entries.setdefault("openai", {})["enabled"] = True
    allow = plugins.setdefault("allow", [])
    for p in ("codex", "openai"):
        if p not in allow:
            allow.append(p)

    cfg.setdefault("auth", {}).setdefault("order", {})
    cfg["auth"]["order"]["openai"] = ["openai-codex:default", "openai:default"]
    cfg["auth"]["order"]["openai-codex"] = ["openai-codex:default"]

    defaults = cfg.setdefault("agents", {}).setdefault("defaults", {})
    if isinstance(defaults.get("model"), dict):
        defaults["model"]["primary"] = defaults["model"].get("primary") or "openai/gpt-5.4"
    else:
        defaults["model"] = "openai/gpt-5.4"

    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    print("Updated openclaw.json: codex enabled, auth.order set")

    if not SOURCE_AUTH.exists():
        print("WARN: no main auth-profiles.json — run: openclaw models auth login --provider openai-codex")
        return

    for agent_id in AGENT_IDS:
        agent_dir = ROOT / "agents" / agent_id / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        dest_auth = agent_dir / "auth-profiles.json"
        shutil.copy2(SOURCE_AUTH, dest_auth)
        if SOURCE_CODEX.exists():
            dest_codex = agent_dir / "codex-home"
            if dest_codex.exists():
                shutil.rmtree(dest_codex)
            shutil.copytree(SOURCE_CODEX, dest_codex)
        print(f"  synced auth -> {agent_id}")

    print("Done. Restart gateway if auth errors persist.")


if __name__ == "__main__":
    main()
