#!/usr/bin/env python3

"""Sanitize openclaw.json for Clawsum multi-agent stack."""

import json

import sys

from pathlib import Path



SCRIPT_DIR = Path(__file__).resolve().parent

if str(SCRIPT_DIR) not in sys.path:

    sys.path.insert(0, str(SCRIPT_DIR))



import ghl_accounts as ghl



CONFIG = Path("/docker/clawsum/data/.openclaw/openclaw.json")



AGENTS = [

    {"id": "admin", "name": "Admin", "workspace": "/home/node/.openclaw/workspace-admin", "default": True},

    {"id": "coding", "name": "Coding", "workspace": "/home/node/.openclaw/workspace-coding"},

    {"id": "data", "name": "Data", "workspace": "/home/node/.openclaw/workspace-data"},

    {"id": "realestate", "name": "Real Estate", "workspace": "/home/node/.openclaw/workspace-realestate"},

]

for acc in ghl.accounts():

    AGENTS.append(

        {

            "id": acc["id"],

            "name": acc["display_name"],

            "workspace": ghl.workspace_path(acc["id"]),

            "tools": ghl.ghl_tool_policy(),

        }

    )

_sb = ghl.sandbox()
if _sb:
    AGENTS.append(
        {
            "id": _sb["id"],
            "name": _sb["name"],
            "workspace": ghl.workspace_path(_sb["id"]),
            "tools": ghl.sandbox_tool_policy(),
        }
    )

AGENTS.extend(

    [

        {"id": "comms", "name": "Comms", "workspace": "/home/node/.openclaw/workspace-comms"},

        {"id": "research", "name": "Research", "workspace": "/home/node/.openclaw/workspace-research"},

        {"id": "planning", "name": "Planning", "workspace": "/home/node/.openclaw/workspace-planning"},

        {"id": "paperclip", "name": "Paperclip", "workspace": "/home/node/.openclaw/workspace-paperclip"},

    ]

)



TOOL_POLICIES = {

    "admin": {"allow": ["read", "write", "edit", "sessions_list", "sessions_history", "session_status"], "deny": ["exec"]},

    "coding": {"allow": ["read", "write", "edit", "apply_patch", "exec", "browser"], "deny": []},

    "data": {"allow": ["read", "write", "exec"], "deny": []},

    "realestate": {"allow": ["read", "write", "browser"], "deny": ["exec"]},

    "comms": {"allow": ["read", "write"], "deny": ["exec", "apply_patch"]},

    "research": {"allow": ["read", "write", "browser"], "deny": ["exec"]},

    "planning": {"allow": ["read", "write"], "deny": ["exec"]},

    "paperclip": {

        "allow": ["read", "write", "edit", "sessions_list", "sessions_history", "session_status"],

        "deny": ["exec"],

    },

}

for acc in ghl.accounts():
    TOOL_POLICIES[acc["id"]] = ghl.ghl_tool_policy()

if ghl.sandbox():
    TOOL_POLICIES[ghl.SANDBOX_AGENT_ID] = ghl.sandbox_tool_policy()



def main():

    cfg = json.loads(CONFIG.read_text())

    defaults = cfg.setdefault("agents", {}).setdefault("defaults", {})

    defaults["workspace"] = "/home/node/.openclaw/workspace-admin"

    defaults.setdefault("skipBootstrap", True)



    enriched = []

    for a in AGENTS:

        entry = dict(a)

        tid = a["id"]

        if tid in TOOL_POLICIES and "tools" not in entry:

            entry["tools"] = TOOL_POLICIES[tid]

        enriched.append(entry)

    cfg["agents"]["list"] = enriched



    cfg.setdefault("channels", {}).setdefault("telegram", {})["enabled"] = False

    cfg.setdefault("channels", {})["whatsapp"] = {

        "enabled": False,

        "dmPolicy": "allowlist",

        "selfChatMode": True,

        "groupPolicy": "allowlist",

    }



    plugins = cfg.setdefault("plugins", {})

    plugins.setdefault("entries", {})

    for p in ["telegram", "whatsapp", "openai", "openrouter", "anthropic", "google", "xai", "browser", "microsoft"]:

        plugins["entries"].setdefault(p, {"enabled": p in ("openai", "openrouter", "anthropic", "google", "xai", "browser", "microsoft")})

    plugins["entries"]["telegram"] = {"enabled": False}

    plugins["entries"]["whatsapp"] = {"enabled": False}

    plugins["allow"] = ["telegram", "whatsapp", "openai", "openrouter", "anthropic", "google", "xai", "browser", "microsoft"]



    cfg["tools"] = cfg.get("tools") or {}

    cfg["tools"]["agentToAgent"] = {"enabled": False}



    bindings = cfg.get("bindings") or []
    cfg["bindings"] = bindings



    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")

    CONFIG.chmod(0o600)

    print("Wrote", CONFIG)

    print("Agents:", [a["id"] for a in enriched])



if __name__ == "__main__":

    main()

