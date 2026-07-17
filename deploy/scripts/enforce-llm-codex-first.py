#!/usr/bin/env python3
"""
Enforce Clawsum LLM policy: ChatGPT Plus (Codex OAuth) first, OpenAI API key backup only.

- openclaw.json: auth.order openai -> [openai-codex:*, openai:default]
- Sync Codex OAuth to all OpenClaw agents
- Verify API key profile exists as fallback (does not remove it)
- Report Hermes/Paperclip caveat (API in container unless task uses OpenClaw agent)

Run on VPS:
  python3 /docker/clawsum/scripts/enforce-llm-codex-first.py
  cd /docker/clawsum && docker compose restart openclaw-gateway
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/docker/clawsum")
OPENCLAW = ROOT / "data/.openclaw"
CONFIG = OPENCLAW / "openclaw.json"
ENV = ROOT / ".env"
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl

AGENTS = ghl.all_clawsum_openclaw_agent_ids()

CODEX_FIRST = ["openai-codex:default", "openai:default"]


def load_env_keys() -> dict[str, bool]:
    keys = {
        "OPENAI_API_KEY": False,
        "ANTHROPIC_API_KEY": False,
        "OPENROUTER_API_KEY": False,
    }
    if not ENV.exists():
        return keys
    for line in ENV.read_text().splitlines():
        line = line.strip()
        for name in keys:
            if line.startswith(f"{name}="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                keys[name] = bool(val)
    return keys


def patch_openclaw_config() -> None:
    cfg = json.loads(CONFIG.read_text())
    plugins = cfg.setdefault("plugins", {}).setdefault("entries", {})
    plugins["codex"] = {"enabled": True}
    plugins.setdefault("openai", {})["enabled"] = True
    allow = cfg.setdefault("plugins", {}).setdefault("allow", [])
    for p in ("codex", "openai"):
        if p not in allow:
            allow.append(p)

    order = cfg.setdefault("auth", {}).setdefault("order", {})
    # Resolve actual codex profile id from admin if present
    codex_profile = "openai-codex:default"
    admin_auth = OPENCLAW / "agents/admin/agent/auth-profiles.json"
    if admin_auth.exists():
        data = json.loads(admin_auth.read_text())
        for name, prof in (data.get("profiles") or {}).items():
            if isinstance(prof, dict) and prof.get("provider") == "openai-codex":
                codex_profile = name
                break

    order["openai"] = [codex_profile, "openai:default"]
    order["openai-codex"] = [codex_profile]

    defaults = cfg.setdefault("agents", {}).setdefault("defaults", {})
    if isinstance(defaults.get("model"), dict):
        defaults["model"]["primary"] = defaults["model"].get("primary") or "openai/gpt-5.4"
    else:
        defaults["model"] = "openai/gpt-5.4"

    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"openclaw.json: auth.order.openai = {order['openai']}")


def verify_agents() -> bool:
    ok = True
    for agent_id in AGENTS:
        auth = OPENCLAW / "agents" / agent_id / "agent" / "auth-profiles.json"
        if not auth.exists():
            print(f"  WARN {agent_id}: no auth-profiles.json")
            ok = False
            continue
        data = json.loads(auth.read_text())
        profiles = data.get("profiles") or {}
        has_codex = any(
            isinstance(p, dict) and p.get("provider") == "openai-codex"
            for p in profiles.values()
        )
        has_api = "openai:default" in profiles
        codex_home = (OPENCLAW / "agents" / agent_id / "agent" / "codex-home").exists()
        flag = "OK" if has_codex and has_api else "WARN"
        if not has_codex:
            ok = False
        print(
            f"  {flag} {agent_id}: codex={has_codex} api_fallback={has_api} codex_home={codex_home}"
        )
    return ok


def main() -> None:
    print("=== Clawsum LLM policy: Codex (ChatGPT Plus) first, API key backup ===\n")

    env_keys = load_env_keys()
    print("Env keys (set / empty):")
    print(f"  OPENAI_API_KEY: {'set' if env_keys['OPENAI_API_KEY'] else 'EMPTY'}")
    print(
        f"  ANTHROPIC_API_KEY: {'set' if env_keys['ANTHROPIC_API_KEY'] else 'EMPTY (not used by OpenClaw agents)'}"
    )
    print(
        f"  OPENROUTER_API_KEY: {'set' if env_keys['OPENROUTER_API_KEY'] else 'EMPTY (no escalation models)'}"
    )

    if not CONFIG.exists():
        raise SystemExit(f"Missing {CONFIG}")

    patch_openclaw_config()

    sync = SCRIPT_DIR / "sync-codex-auth-all-agents.py"
    if sync.exists():
        print("\nRunning sync-codex-auth-all-agents.py ...")
        subprocess.run([sys.executable, str(sync)], check=False)

    print("\nAgent verification:")
    ok = verify_agents()

    print("\n--- Hermes / Paperclip note ---")
    print(
        "Tasks assigned to OpenClaw agents (Admin, Data, …) use gateway Codex OAuth → ChatGPT Plus."
    )
    print(
        "Tasks assigned to Clawsum Hermes use hermes_local + OPENAI_API_KEY in Paperclip container."
    )
    print(
        "Prefer OpenClaw assignees for subscription billing; use Hermes only for long autonomous runs."
    )
    if env_keys["ANTHROPIC_API_KEY"]:
        print(
            "ANTHROPIC_API_KEY is set in .env but OpenClaw agents are configured for OpenAI/Codex only."
        )

    or_script = SCRIPT_DIR / "configure-openrouter-escalation.py"
    if env_keys["OPENROUTER_API_KEY"] and or_script.exists():
        print("\n--- OpenRouter escalation ---")
        subprocess.run([sys.executable, str(or_script)], check=False)

    print("\nRestart gateway:")
    print("  cd /docker/clawsum && docker compose restart openclaw-gateway")

    if not ok:
        print("\nACTION: Complete Codex login:")
        print(
            "  ssh -t clawsum \"cd /docker/clawsum && docker compose run --rm openclaw-cli models auth login --provider openai-codex --device-code\""
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
