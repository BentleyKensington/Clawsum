#!/usr/bin/env python3
"""Verify GHL multi-account isolation boundaries on Clawsum."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl  # noqa: E402

ROOT = Path("/docker/clawsum")
OPENCLAW = ROOT / "data" / ".openclaw"
CONFIG = OPENCLAW / "openclaw.json"
OBS = ROOT / "obsidian"

FAILURES: list[str] = []
WARNINGS: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def warn(msg: str) -> None:
    WARNINGS.append(msg)


def ok(msg: str) -> None:
    print(f"OK  {msg}")


def check_openclaw() -> None:
    if not CONFIG.exists():
        fail(f"missing {CONFIG}")
        return
    cfg = json.loads(CONFIG.read_text())
    agents = {a["id"]: a for a in cfg.get("agents", {}).get("list", [])}
    mcp_servers = (cfg.get("mcp") or {}).get("servers") or {}

    sb = ghl.sandbox()
    if sb:
        sid = sb["id"]
        if sid not in agents:
            warn(f"optional sandbox agent '{sid}' missing")
        else:
            tools = agents[sid].get("tools") or {}
            deny = set(tools.get("deny") or [])
            if "write" not in deny:
                warn(f"{sid} should deny write")
            ok(f"{sid} sandbox present")

    for acc in ghl.accounts():
        aid = acc["id"]
        if aid not in agents:
            fail(f"missing agent {aid}")
            continue
        entry = agents[aid]
        allowed = (cfg.get("mcp") or {}).get("servers", {}).get(acc["mcp_server"], {})
        codex_agents = (allowed.get("codex") or {}).get("agents") or []
        if codex_agents != [aid]:
            fail(f"{aid}: MCP codex.agents must be [{aid}] got {codex_agents}")
        else:
            ok(f"{aid} MCP scoped via codex.agents")
        if acc["mcp_server"] not in mcp_servers:
            warn(f"MCP server definition missing for {acc['mcp_server']} (credentials pending?)")
        ws = Path(ghl.workspace_path(aid).replace("/home/node/.openclaw", str(OPENCLAW)))
        if not ws.exists():
            fail(f"workspace missing: {ws}")
        else:
            ok(f"workspace {aid}")

    bindings = cfg.get("bindings") or []
    agent_groups: dict[str, list[str]] = {}
    for b in bindings:
        aid = b.get("agentId")
        gid = b.get("match", {}).get("peer", {}).get("id")
        if aid and gid:
            agent_groups.setdefault(aid, []).append(gid)
    for aid, gids in agent_groups.items():
        if len(gids) != len(set(gids)):
            warn(f"duplicate group bindings for {aid}")

    if not (cfg.get("tools") or {}).get("agentToAgent", {}).get("enabled") is False:
        warn("agentToAgent should be disabled")

    ok("openclaw.json checks complete")


def check_obsidian() -> None:
    for acc in ghl.accounts():
        folder = OBS / "GHL" / acc["obsidian_folder"]
        if not folder.exists():
            fail(f"Obsidian folder missing: {folder}")
        else:
            ok(f"Obsidian {acc['obsidian_folder']}")


def check_postgres() -> None:
    schemas = [acc["schema_prefix"] for acc in ghl.accounts()]
    if not schemas:
        warn("no GHL accounts in ghl-accounts.json")
        return
    in_list = ",".join(f"'{s}'" for s in schemas)
    try:
        out = subprocess.run(
            [
                "docker",
                "exec",
                "clawsum-postgres-1",
                "psql",
                "-U",
                "clawsum",
                "-d",
                "ghl",
                "-tAc",
                f"SELECT schema_name FROM information_schema.schemata "
                f"WHERE schema_name IN ({in_list});",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        warn(f"Postgres check skipped: {e}")
        return
    if out.returncode != 0:
        warn(f"Postgres check failed: {out.stderr.strip()}")
        return
    found = {s.strip() for s in out.stdout.splitlines() if s.strip()}
    for acc in ghl.accounts():
        schema = acc["schema_prefix"]
        if schema not in found:
            fail(f"Postgres schema missing: {schema}")
        else:
            ok(f"Postgres schema {schema}")


def check_workspaces_soul() -> None:
    for acc in ghl.accounts():
        soul = OPENCLAW / f"workspace-{acc['id']}" / "SOUL.md"
        if not soul.exists():
            fail(f"SOUL.md missing for {acc['id']}")
            continue
        text = soul.read_text()
        if acc["display_name"] not in text and acc["obsidian_folder"] not in text:
            warn(f"SOUL.md for {acc['id']} may not be account-scoped")
        if "Never" not in text and "never" not in text.lower():
            warn(f"SOUL.md for {acc['id']} missing boundary language")
        ok(f"SOUL.md {acc['id']}")


def main() -> None:
    print("=== GHL isolation verification ===\n")
    check_openclaw()
    check_obsidian()
    check_workspaces_soul()
    check_postgres()

    print()
    for w in WARNINGS:
        print(f"WARN {w}")
    for f in FAILURES:
        print(f"FAIL {f}")

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s), {len(WARNINGS)} warning(s)")
        sys.exit(1)
    print(f"\nAll checks passed ({len(WARNINGS)} warning(s))")


if __name__ == "__main__":
    main()
