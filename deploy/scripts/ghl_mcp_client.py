#!/usr/bin/env python3
"""Shared GHL MCP + Postgres helpers for audit scripts."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
OBS = ROOT / "obsidian"
GATEWAY_JS = SCRIPT_DIR / "ghl_mcp_gateway.js"
GATEWAY_JS_CONTAINER = "/home/node/obsidian/_tools/ghl_mcp_gateway.js"


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def ensure_gateway_js() -> tuple[str, Path]:
    src = GATEWAY_JS if GATEWAY_JS.exists() else SCRIPT_DIR / "ghl_mcp_gateway.js"
    dest = OBS / "_tools" / "ghl_mcp_gateway.js"
    out_host = OBS / "_tools" / "mcp_out.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    subprocess.run(["chown", "-R", "1000:1000", str(dest.parent)], check=False)
    return GATEWAY_JS_CONTAINER, out_host


def mcp_call(
    cmd: str,
    *args: str,
    pit: str,
    location_id: str,
    compact_limit: str = "500",
    timeout: int = 180,
) -> dict[str, Any]:
    js_in_container, out_host = ensure_gateway_js()
    out_container = "/home/node/obsidian/_tools/mcp_out.json"
    proc = subprocess.run(
        [
            "docker",
            "exec",
            "-e",
            f"GHL_PIT={pit}",
            "-e",
            f"GHL_LOCATION_ID={location_id}",
            "-e",
            f"GHL_MCP_OUTFILE={out_container}",
            "-e",
            f"GHL_COMPACT_LIMIT={compact_limit}",
            "clawsum-openclaw-gateway-1",
            "node",
            js_in_container,
            cmd,
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0 and not out_host.exists():
        raise RuntimeError(f"MCP failed: {proc.stderr[:400] or proc.stdout[:400]}")
    if out_host.exists():
        return json.loads(out_host.read_text(encoding="utf-8"))
    return json.loads(proc.stdout.strip() or "{}")


def mcp_tool(
    name: str,
    arguments: dict[str, Any],
    pit: str,
    location_id: str,
    available: set[str] | None = None,
    compact_limit: str = "500",
) -> Any:
    if available is not None and name not in available:
        return {"_skipped": True, "_reason": "tool not available"}
    resp = mcp_call(
        "call",
        name,
        json.dumps(arguments),
        pit=pit,
        location_id=location_id,
        compact_limit=compact_limit,
    )
    if not resp.get("ok"):
        return {"_error": resp.get("parsed") or resp.get("status")}
    if resp.get("compact") is not None:
        return resp["compact"]
    return resp.get("compact") or resp.get("parsed")


def mcp_tools_list(pit: str, location_id: str) -> tuple[set[str], list[str]]:
    resp = mcp_call("tools/list", pit=pit, location_id=location_id, compact_limit="100")
    names = resp.get("toolNames") or []
    return set(names), list(names)


def sync_db_password(account: dict[str, Any], env: dict[str, str]) -> str:
    import ghl_accounts as ghl

    pw = env.get(account["env_db_password"], "").strip()
    if not pw:
        raise SystemExit(f"Missing {account['env_db_password']} in .env")
    role = ghl.db_role_for(account)
    safe = pw.replace("'", "''")
    schema = account["schema_prefix"]
    subprocess.run(
        [
            "docker",
            "exec",
            "clawsum-postgres-1",
            "psql",
            "-U",
            "clawsum",
            "-d",
            "ghl",
            "-c",
            f"ALTER ROLE {role} PASSWORD '{safe}'; "
            f"GRANT CREATE ON SCHEMA {schema} TO {role};",
        ],
        check=True,
        capture_output=True,
    )
    return pw


def psql_as_account(account: dict[str, Any], password: str, sql: str) -> str:
    import ghl_accounts as ghl

    env_pg = {**os.environ, "PGPASSWORD": password}
    role = ghl.db_role_for(account)
    out = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "clawsum-postgres-1",
            "psql",
            "-U",
            role,
            "-d",
            "ghl",
            "-v",
            "ON_ERROR_STOP=1",
            "-tA",
        ],
        input=sql.encode(),
        capture_output=True,
        env=env_pg,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.decode()[:500])
    return out.stdout.decode()


def sql_quote(val: str | None) -> str:
    if val is None:
        return "NULL"
    return "'" + val.replace("'", "''") + "'"
