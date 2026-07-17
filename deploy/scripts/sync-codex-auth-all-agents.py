#!/usr/bin/env python3
"""Copy Codex OAuth auth from admin (or any agent with openai-codex) to all agents."""
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

AGENTS = ghl.all_clawsum_openclaw_agent_ids()


def find_codex_source():
    for agent_id in AGENTS:
        auth = ROOT / "agents" / agent_id / "agent" / "auth-profiles.json"
        if not auth.exists():
            continue
        data = json.loads(auth.read_text())
        for prof in (data.get("profiles") or {}).values():
            if isinstance(prof, dict) and prof.get("provider") == "openai-codex":
                codex = ROOT / "agents" / agent_id / "agent" / "codex-home"
                return agent_id, auth, codex if codex.exists() else None
    return None, None, None


def sync_agent(agent_id: str, src_auth: Path, src_codex: Path | None) -> None:
    agent_dir = ROOT / "agents" / agent_id / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    dest_auth = agent_dir / "auth-profiles.json"
    shutil.copy2(src_auth, dest_auth)
    dest_auth.chmod(0o600)
    if src_codex and src_codex.exists():
        dest_codex = agent_dir / "codex-home"
        if dest_codex.exists():
            shutil.rmtree(dest_codex)
        shutil.copytree(src_codex, dest_codex)
    print(f"  synced -> {agent_id}")


def main():
    src_id, src_auth, src_codex = find_codex_source()
    if not src_auth:
        print("No openai-codex auth profile found in any agent")
        raise SystemExit(1)
    print(f"Source: {src_id}")
    for agent_id in AGENTS:
        if agent_id == src_id:
            continue
        sync_agent(agent_id, src_auth, src_codex)
    print("Done.")


if __name__ == "__main__":
    main()
