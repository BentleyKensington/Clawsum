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

        {"id": "media", "name": "Media", "workspace": "/home/node/.openclaw/workspace-media"},
        {"id": "pentest", "name": "Pentest", "workspace": "/home/node/.openclaw/workspace-pentest"},
        {"id": "content", "name": "Content", "workspace": "/home/node/.openclaw/workspace-content"},
        {"id": "social", "name": "Social", "workspace": "/home/node/.openclaw/workspace-social"},
        {"id": "closebot", "name": "CloseBot", "workspace": "/home/node/.openclaw/workspace-closebot"},
        {"id": "printful", "name": "Printful", "workspace": "/home/node/.openclaw/workspace-printful"},
        {"id": "shopify", "name": "Shopify", "workspace": "/home/node/.openclaw/workspace-shopify"},
        {"id": "seo-aeo-geo", "name": "SEO AEO GEO", "workspace": "/home/node/.openclaw/workspace-seo-aeo-geo"},
        {"id": "meta-ads", "name": "Meta Ads", "workspace": "/home/node/.openclaw/workspace-meta-ads"},
        {"id": "acceptai", "name": "AcceptAI", "workspace": "/home/node/.openclaw/workspace-acceptai"},
        {"id": "calendar", "name": "Calendar", "workspace": "/home/node/.openclaw/workspace-calendar"},
        {"id": "slack-avenou", "name": "Slack Avenou", "workspace": "/home/node/.openclaw/workspace-slack-avenou"},
        {"id": "vocalitic", "name": "Vocalitic", "workspace": "/home/node/.openclaw/workspace-vocalitic"},
        {"id": "llm-lab", "name": "LLM Lab", "workspace": "/home/node/.openclaw/workspace-llm-lab"},
        {"id": "vapi", "name": "VAPI", "workspace": "/home/node/.openclaw/workspace-vapi"},
        {"id": "sellthebizfast", "name": "SellTheBizFast", "workspace": "/home/node/.openclaw/workspace-sellthebizfast"},
        {"id": "rocco", "name": "Rocco Secure", "workspace": "/home/node/.openclaw/workspace-rocco"},

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

    # Media needs exec for FFmpeg, yt-dlp, Whisper, auto-editor on GPU host.
    "media": {"allow": ["read", "write", "edit", "exec", "browser"], "deny": []},
    # Pentest: defensive scans only (scripts); no exploit payloads in policy/docs.
    "pentest": {"allow": ["read", "write", "edit", "exec", "browser"], "deny": []},
    "content": {"allow": ["read", "write", "edit", "exec"], "deny": []},
    "social": {"allow": ["read", "write", "edit"], "deny": ["exec"]},
    "closebot": {"allow": ["read", "write", "browser", "exec"], "deny": ["apply_patch"]},
    "printful": {"allow": ["read", "write", "browser"], "deny": ["exec", "apply_patch"]},
    "shopify": {"allow": ["read", "write", "browser"], "deny": ["exec", "apply_patch"]},
    "seo-aeo-geo": {"allow": ["read", "write", "browser"], "deny": ["exec", "apply_patch"]},
    "meta-ads": {"allow": ["read", "write", "browser"], "deny": ["exec", "apply_patch"]},
    "acceptai": {"allow": ["read", "write", "browser", "exec"], "deny": ["apply_patch"]},
    "calendar": {"allow": ["read", "write"], "deny": ["exec", "apply_patch"]},
    "slack-avenou": {"allow": ["read", "write"], "deny": ["exec", "apply_patch"]},
    "vocalitic": {"allow": ["read", "write", "edit", "exec", "browser"], "deny": []},
    "llm-lab": {"allow": ["read", "write", "browser", "exec"], "deny": []},
    "vapi": {"allow": ["read", "write", "browser", "exec"], "deny": ["apply_patch"]},
    "sellthebizfast": {"allow": ["read", "write", "browser"], "deny": ["exec", "apply_patch"]},
    "rocco": {"allow": ["read", "write", "edit", "exec", "browser"], "deny": []},

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



    # Preserve existing channel enable flags. Never force Discord/Telegram off —
    # that made chat non-responsive after Media agent provisioning.
    channels = cfg.setdefault("channels", {})
    channels.setdefault("telegram", {}).setdefault("enabled", True)
    channels.setdefault("discord", {}).setdefault("enabled", True)
    channels.setdefault("whatsapp", {
        "enabled": False,
        "dmPolicy": "allowlist",
        "selfChatMode": True,
        "groupPolicy": "allowlist",
    })
    if "enabled" not in channels["whatsapp"]:
        channels["whatsapp"]["enabled"] = False

    plugins = cfg.setdefault("plugins", {})
    plugins.setdefault("entries", {})
    for p in ["telegram", "whatsapp", "discord", "openai", "openrouter", "anthropic", "google", "xai", "browser", "microsoft"]:
        default_on = p in ("openai", "openrouter", "anthropic", "google", "xai", "browser", "microsoft", "discord", "telegram")
        plugins["entries"].setdefault(p, {"enabled": default_on})
    # Keep Discord/Telegram plugins on unless explicitly disabled already as False by operator.
    # Only force WhatsApp off by default for this stack.
    plugins["entries"].setdefault("whatsapp", {"enabled": False})
    plugins["entries"]["whatsapp"] = {"enabled": False}
    if plugins["entries"].get("discord", {}).get("enabled") is not True:
        plugins["entries"]["discord"] = {"enabled": True}
    if plugins["entries"].get("telegram", {}).get("enabled") is not True:
        plugins["entries"]["telegram"] = {"enabled": True}
    plugins["allow"] = ["telegram", "whatsapp", "discord", "openai", "openrouter", "anthropic", "google", "xai", "browser", "microsoft"]



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

