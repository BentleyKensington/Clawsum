#!/usr/bin/env python3
"""Shared GHL multi-account definitions for Clawsum (one gateway, isolated agents)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path("/docker/clawsum")
REPO_ROOT = Path(__file__).resolve().parent.parent

CONFIG_CANDIDATES = [
    ROOT / "config" / "ghl-accounts.json",
    REPO_ROOT / "config" / "ghl-accounts.json",
]

GHL_MCP_URL = "https://services.leadconnectorhq.com/mcp/"
SANDBOX_AGENT_ID = "ghl-template"  # optional; not in generic template default

BASE_TELEGRAM_ROUTES: list[tuple[str, str]] = [
    ("paperclip", "paperclip"),
    ("ops", "admin"),
    ("coding", "coding"),
    ("data", "data"),
    ("real estate", "realestate"),
    ("realestate", "realestate"),
    ("comms", "comms"),
    ("research", "research"),
    ("planning", "planning"),
    ("admin", "admin"),
]

GHL_GENERIC_KEYWORDS = [
    "ghl",
    "gohighlevel",
    "highlevel",
    "pipeline",
    "a2p",
    "crm",
    "funnel",
    "vapi",
    "stripe",
]


def config_path() -> Path:
    for path in CONFIG_CANDIDATES:
        if path.exists():
            return path
    return CONFIG_CANDIDATES[-1]


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        raise FileNotFoundError(f"GHL accounts config not found: {path}")
    return json.loads(path.read_text())


def sandbox() -> dict[str, Any] | None:
    return load_config().get("sandbox")


def delegation_rules() -> list[tuple[str, list[str]]]:
    return [
        (acc["paperclip_name"], list(acc.get("telegram_needles", [])))
        for acc in accounts()
    ]


def accounts() -> list[dict[str, Any]]:
    return load_config()["accounts"]


def account_by_id(agent_id: str) -> dict[str, Any] | None:
    for acc in accounts():
        if acc["id"] == agent_id:
            return acc
    return None


def account_by_slug(slug: str) -> dict[str, Any] | None:
    for acc in accounts():
        if acc["slug"] == slug:
            return acc
    return None


def db_role_for(account: dict[str, Any]) -> str:
    return f"ghl_{account['schema_prefix']}"


def openclaw_agent_ids(*, include_sandbox: bool = False) -> list[str]:
    ids = [acc["id"] for acc in accounts()]
    if include_sandbox and sandbox():
        ids.append(SANDBOX_AGENT_ID)
    return ids


def all_clawsum_openclaw_agent_ids() -> list[str]:
    """Full gateway roster for generic template + optional sandbox."""
    base = [
        "admin",
        "coding",
        "data",
        "realestate",
        "comms",
        "research",
        "planning",
        "paperclip",
    ]
    return base + openclaw_agent_ids(include_sandbox=bool(sandbox()))


def telegram_routes() -> list[tuple[str, str]]:
    """Account-specific routes first — never map generic 'ghl' to a live agent."""
    routes: list[tuple[str, str]] = []
    for acc in accounts():
        for needle in acc.get("telegram_needles", []):
            routes.append((needle.lower(), acc["id"]))
    return routes + BASE_TELEGRAM_ROUTES


def match_telegram_agent(title: str) -> str | None:
    t = (title or "").lower()
    for needle, agent_id in telegram_routes():
        if needle in t:
            return agent_id
    return None


def paperclip_agents() -> list[tuple[str, str, str]]:
    """(name, openclaw_id, capabilities) for wire-paperclip-clawsum."""
    out: list[tuple[str, str, str]] = []
    for acc in accounts():
        out.append(
            (
                acc["paperclip_name"],
                acc["id"],
                f"GoHighLevel — {acc['display_name']} CRM (isolated).",
            )
        )
    return out


def paperclip_name_to_openclaw_id() -> dict[str, str]:
    mapping = {
        "Clawsum Admin": "admin",
        "Clawsum Coding": "coding",
        "Clawsum Data": "data",
        "Clawsum RE": "realestate",
        "Clawsum Comms": "comms",
        "Clawsum Research": "research",
        "Clawsum Planning": "planning",
        "Clawsum Paperclip": "paperclip",
        "Clawsum Hermes": "hermes",
    }
    for acc in accounts():
        mapping[acc["paperclip_name"]] = acc["id"]
    return mapping


def paperclip_agent_names() -> list[str]:
    names = [
        "Clawsum Admin",
        "Clawsum Coding",
        "Clawsum Data",
        "Clawsum RE",
        "Clawsum Comms",
        "Clawsum Research",
        "Clawsum Planning",
        "Clawsum Paperclip",
    ]
    names[4:4] = [acc["paperclip_name"] for acc in accounts()]
    return names


def guess_ghl_paperclip_agent(text: str) -> str | None:
    low = text.lower()
    for name, needles in delegation_rules():
        if any(n in low for n in needles):
            return name
    if any(k in low for k in GHL_GENERIC_KEYWORDS):
        accs = accounts()
        if len(accs) == 1:
            return accs[0]["paperclip_name"]
        return None
    return None


def ghl_tool_policy() -> dict[str, list[str]]:
    return {
        "allow": ["read", "write"],
        "deny": ["exec", "browser", "search", "grep", "glob", "find", "rg"],
    }


def sandbox_tool_policy() -> dict[str, list[str]]:
    return {
        "allow": ["read"],
        "deny": ["write", "edit", "exec", "browser", "apply_patch"],
    }


def workspace_path(agent_id: str) -> str:
    return f"/home/node/.openclaw/workspace-{agent_id}"


def mcp_server_def(account: dict[str, Any], *, enabled: bool) -> dict[str, Any]:
    return {
        "url": GHL_MCP_URL,
        "transport": "streamable-http",
        "enabled": enabled,
        "headers": {
            "Authorization": f"Bearer ${{{account['env_pit']}}}",
            "locationId": f"${{{account['env_location']}}}",
        },
    }
