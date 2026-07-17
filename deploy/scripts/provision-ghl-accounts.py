#!/usr/bin/env python3
"""
Provision GHL account agent(s) on Clawsum (one gateway, isolated per location).

- Seeds workspaces from templates/ghl/ per ghl-accounts.json
- Optional ghl-template sandbox when "sandbox" key present in config
- Postgres schemas + roles, Obsidian folders, workspaces, Paperclip agents

Usage (VPS):
  python3 /docker/clawsum/scripts/provision-ghl-accounts.py
  python3 /docker/clawsum/scripts/provision-ghl-accounts.py --dry-run
  python3 /docker/clawsum/scripts/provision-ghl-accounts.py --skip-paperclip --skip-postgres
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl  # noqa: E402

ROOT = Path("/docker/clawsum")
OPENCLAW = ROOT / "data" / ".openclaw"
CONFIG = OPENCLAW / "openclaw.json"
ENV_FILE = ROOT / ".env"
OBS = ROOT / "obsidian"
TEMPLATES = ROOT / "templates" / "ghl"
REPO_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "ghl"
LEGACY_TEMPLATES = ROOT / "templates" / "ghl-account"
LEGACY_REPO_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "ghl-account"

API = os.environ.get("PAPERCLIP_API", "http://127.0.0.1:3100/api")
COMPANY_ID = os.environ.get(
    "PAPERCLIP_COMPANY_ID", ""
)
GW_HTTP = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:48166")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        out.setdefault(k, v)
    return out


def tpl_dir() -> Path:
    for path in (TEMPLATES, REPO_TEMPLATES, LEGACY_TEMPLATES, LEGACY_REPO_TEMPLATES):
        if path.exists():
            return path
    return REPO_TEMPLATES


def render_template(name: str, account: dict, location_id: str = "PENDING") -> str:
    path = tpl_dir() / name
    text = path.read_text()
    subs = {
        "{DISPLAY_NAME}": account["display_name"],
        "{LOCATION_ID}": location_id,
        "{SCHEMA_PREFIX}": account["schema_prefix"],
        "{OBSIDIAN_FOLDER}": account["obsidian_folder"],
        "{AGENT_ID}": account["id"],
        "{SLUG}": account["slug"],
        "{DB_USER}": f"ghl_{account['schema_prefix']}",
        "{ENV_DB_PASSWORD}": account["env_db_password"],
    }
    for key, val in subs.items():
        text = text.replace(key, val)
    return text


def migrate_legacy_ghl_workspace(dry_run: bool) -> None:
    legacy = OPENCLAW / "workspace-ghl"
    sandbox_ws = OPENCLAW / f"workspace-{ghl.SANDBOX_AGENT_ID}"
    if not legacy.exists():
        return
    if sandbox_ws.exists():
        print(f"SKIP migrate: {sandbox_ws} already exists")
        return
    print(f"MIGRATE {legacy} -> {sandbox_ws}")
    if not dry_run:
        shutil.copytree(legacy, sandbox_ws)
        subprocess.run(["chown", "-R", "1000:1000", str(sandbox_ws)], check=False)


def seed_sandbox_workspace(dry_run: bool) -> None:
    sb = ghl.sandbox()
    if not sb:
        return
    ws = OPENCLAW / f"workspace-{sb['id']}"
    if ws.exists():
        return
    print(f"CREATE sandbox workspace {ws}")
    if dry_run:
        return
    ws.mkdir(parents=True)
    for sub in ("memory", "notes", "projects"):
        (ws / sub).mkdir(exist_ok=True)
    admin = OPENCLAW / "workspace-admin"
    for fname in ("SECURITY.md", "USER.md", "AGENTS.md"):
        src = admin / fname
        if src.exists():
            shutil.copy2(src, ws / fname)
    soul = f"""# SOUL.md — GHL template (sandbox)

This agent is a **read-only sandbox** for the GHL account template. It is **not** wired to any live CRM location.

- **Do not** perform production GHL work here.
- Copy `templates/ghl-account/` and run `provision-ghl-accounts.py` for live accounts.
- Live agents: configured in `config/ghl-accounts.json` (run `provision-ghl-accounts.py`).

## Shared boundaries (all Clawsum agents)

- Private things stay private. Never leak secrets or the operator's context.
- Ask Boss before external actions.
- Stay in this workspace unless Boss approves otherwise.
"""
    (ws / "SOUL.md").write_text(soul)
    (ws / "IDENTITY.md").write_text(
        "# IDENTITY.md\n\n"
        "- **Name:** GHL Template (Sandbox)\n"
        "- **Emoji:** 📋\n"
        "- **Creature:** Clawsum template agent\n"
        "- **Vibe:** Reference only — not production\n"
    )
    (ws / "WORKFLOWS.md").write_text(
        "# WORKFLOWS.md — GHL template\n\n"
        "Template reference only. See `/docker/clawsum/templates/ghl-account/`.\n"
    )
    subprocess.run(["chown", "-R", "1000:1000", str(ws)], check=False)


def seed_account_workspace(account: dict, env: dict[str, str], dry_run: bool) -> None:
    ws = OPENCLAW / f"workspace-{account['id']}"
    if dry_run:
        print(f"WOULD seed workspace {ws}")
        return
    ws.mkdir(parents=True, exist_ok=True)
    for sub in ("memory", "notes", "projects"):
        (ws / sub).mkdir(exist_ok=True)
    admin = OPENCLAW / "workspace-admin"
    for fname in ("SECURITY.md", "USER.md"):
        src = admin / fname
        if src.exists() and not (ws / fname).exists():
            shutil.copy2(src, ws / fname)

    loc = env.get(account["env_location"], "PENDING")
    for tpl in (
        "SOUL.md",
        "WORKFLOWS.md",
        "ESCALATION.md",
        "OBSIDIAN.md",
        "DATABASE.md",
        "AGENTS.md",
        "TOOLS.md",
    ):
        src = tpl_dir() / tpl
        if src.exists():
            (ws / tpl).write_text(render_template(tpl, account, loc))

    (ws / "IDENTITY.md").write_text(
        f"# IDENTITY.md\n\n"
        f"- **Name:** {account['identity_name']}\n"
        f"- **Emoji:** {account['identity_emoji']}\n"
        f"- **Creature:** Clawsum GHL specialist\n"
        f"- **Vibe:** CRM-focused — {account['display_name']} only\n"
    )
    boot = ws / "BOOT.md"
    boot_text = (
        f"# BOOT.md — {account['id']}\n\n"
        "On session start read: SOUL.md, AGENTS.md, TOOLS.md, WORKFLOWS.md, SECURITY.md, DATABASE.md, OBSIDIAN.md.\n\n"
        "**Re-engage:** if Boss asks, use **read** on `REENGAGE.md` (workspace root). "
        "Search/grep/browser are **denied** and will fail.\n"
    )
    boot.write_text(boot_text)
    subprocess.run(["chown", "-R", "1000:1000", str(ws)], check=False)
    print(f"Seeded workspace {account['id']}")


def seed_obsidian(account: dict, dry_run: bool) -> None:
    folder = OBS / "GHL" / account["obsidian_folder"]
    if dry_run:
        print(f"WOULD create Obsidian {folder}")
        return
    for sub in ("Audits", "Recommendations"):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    readme = folder / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# {account['obsidian_folder']}\n\n"
            f"Agent: **{account['id']}**  \n"
            f"GHL location: `{account['display_name']}` only.\n"
        )
    subprocess.run(["chown", "-R", "1000:1000", str(folder)], check=False)


def patch_openclaw(env: dict[str, str], dry_run: bool) -> None:
    cfg = json.loads(CONFIG.read_text())
    agent_list = cfg.setdefault("agents", {}).setdefault("list", [])

    def upsert(entry: dict) -> None:
        nonlocal agent_list
        for i, a in enumerate(agent_list):
            if a.get("id") == entry["id"]:
                agent_list[i] = {**a, **entry}
                return
        agent_list.append(entry)

    sb = ghl.sandbox()
    if sb:
        upsert(
            {
                "id": sb["id"],
                "name": sb["name"],
                "workspace": ghl.workspace_path(sb["id"]),
                "tools": ghl.sandbox_tool_policy(),
            }
        )

    for acc in ghl.accounts():
        creds_ok = bool(
            env.get(acc["env_pit"], "").strip()
            and env.get(acc["env_location"], "").strip()
        )
        upsert(
            {
                "id": acc["id"],
                "name": acc["display_name"],
                "workspace": ghl.workspace_path(acc["id"]),
                "tools": ghl.ghl_tool_policy(),
            }
        )
        print(f"  agent {acc['id']} mcpServers=[{acc['mcp_server']}] enabled={creds_ok}")

    cfg["agents"]["list"] = agent_list

    mcp = cfg.setdefault("mcp", {})
    servers = mcp.setdefault("servers", {})
    for acc in ghl.accounts():
        creds_ok = bool(
            env.get(acc["env_pit"], "").strip()
            and env.get(acc["env_location"], "").strip()
        )
        servers[acc["mcp_server"]] = ghl.mcp_server_def(acc, enabled=creds_ok)
        if isinstance(servers[acc["mcp_server"]], dict):
            servers[acc["mcp_server"]].setdefault("codex", {})["agents"] = [acc["id"]]

    bindings = cfg.get("bindings") or []
    cfg["bindings"] = bindings

    cfg["tools"] = cfg.get("tools") or {}
    cfg["tools"]["agentToAgent"] = {"enabled": False}

    if dry_run:
        print("DRY-RUN openclaw.json patch (agents + mcp + bindings)")
        return
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    CONFIG.chmod(0o600)
    print(f"Wrote {CONFIG}")


def apply_postgres(dry_run: bool) -> None:
    sql_path = ROOT / "postgres-init" / "07-ghl-account-schemas.sql"
    repo_sql = Path(__file__).resolve().parent.parent / "postgres-init" / "07-ghl-account-schemas.sql"
    path = sql_path if sql_path.exists() else repo_sql
    if not path.exists():
        print(f"WARN: missing {path}")
        return
    if dry_run:
        print(f"DRY-RUN postgres: {path}")
        return
    subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "clawsum-postgres-1",
            "psql",
            "-U",
            "clawsum",
            "-d",
            "ghl",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=path.read_bytes(),
        check=True,
    )
    print("Applied Postgres GHL account schemas/roles")


def gateway_ws_url() -> str:
    base = GW_HTTP.replace("https://", "wss://").replace("http://", "ws://").rstrip("/")
    if not base.endswith("/ws"):
        base = base + "/ws"
    return base


def api(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw) if raw else {"error": e.reason}
        except json.JSONDecodeError:
            return e.code, {"error": raw}


def openclaw_adapter(agent_id: str, gw_token: str) -> dict:
    return {
        "url": gateway_ws_url(),
        "agentId": agent_id,
        "sessionKeyStrategy": "fixed",
        "sessionKey": f"paperclip:{agent_id}",
        "headers": {
            "authorization": f"Bearer {gw_token}",
            "x-openclaw-token": gw_token,
        },
        "timeoutSec": 300,
        "waitTimeoutMs": 300000,
        "disableDeviceAuth": True,
        "autoPairOnFirstConnect": False,
        "scopes": ["operator.admin"],
    }


def wire_paperclip(gw_token: str, dry_run: bool) -> None:
    code, agents = api("GET", f"companies/{COMPANY_ID}/agents")
    if code != 200:
        print(f"WARN Paperclip GET agents -> {code}: {agents}")
        return
    by_name = {a.get("name"): a for a in agents if isinstance(a, dict)}

    deprecated = "Clawsum GHL"
    if deprecated in by_name and not dry_run and len(ghl.accounts()) > 1:
        aid = by_name[deprecated]["id"]
        body = {
            "status": "paused",
            "capabilities": "DEPRECATED — use per-account GHL agents from ghl-accounts.json.",
        }
        code, res = api("PATCH", f"agents/{aid}", body)
        print(f"Paused deprecated Paperclip agent '{deprecated}' -> {code}")

    for name, oc_id, capabilities in ghl.paperclip_agents():
        if name in by_name:
            aid = by_name[name]["id"]
            if dry_run:
                print(f"DRY-RUN patch Paperclip {name}")
                continue
            body = {
                "adapterType": "openclaw_gateway",
                "adapterConfig": openclaw_adapter(oc_id, gw_token),
                "capabilities": capabilities,
                "status": "paused",
            }
            code, _ = api("PATCH", f"agents/{aid}", body)
            print(f"Paperclip patch {name} -> {code}")
            continue
        if dry_run:
            print(f"DRY-RUN hire Paperclip {name}")
            continue
        body = {
            "name": name,
            "role": "engineer",
            "title": name.replace("Clawsum GHL — ", "GHL "),
            "capabilities": capabilities,
            "adapterType": "openclaw_gateway",
            "adapterConfig": openclaw_adapter(oc_id, gw_token),
            "budgetMonthlyCents": 50_000,
            "status": "paused",
        }
        code, res = api("POST", f"companies/{COMPANY_ID}/agents", body)
        print(f"Paperclip hire {name} -> {code}")


def copy_config_to_vps(dry_run: bool) -> None:
    """Ensure VPS config dir has ghl-accounts.json."""
    src = Path(__file__).resolve().parent.parent / "config" / "ghl-accounts.json"
    dst = ROOT / "config" / "ghl-accounts.json"
    if src.resolve() == dst.resolve():
        return
    if not src.exists():
        return
    if dry_run:
        print(f"DRY-RUN copy {src} -> {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision GHL multi-account agents")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-postgres", action="store_true")
    parser.add_argument("--skip-paperclip", action="store_true")
    args = parser.parse_args()

    env = load_env()
    copy_config_to_vps(args.dry_run)

    print("==> Migrate / seed workspaces")
    migrate_legacy_ghl_workspace(args.dry_run)
    seed_sandbox_workspace(args.dry_run)
    for acc in ghl.accounts():
        seed_account_workspace(acc, env, args.dry_run)
        seed_obsidian(acc, args.dry_run)

    print("==> Patch openclaw.json")
    if CONFIG.exists():
        patch_openclaw(env, args.dry_run)
    else:
        print(f"WARN: {CONFIG} missing — run on VPS after stack is up")

    if not args.skip_postgres:
        print("==> Postgres schemas/roles")
        apply_postgres(args.dry_run)

    if not args.skip_paperclip:
        gw_token = env.get("OPENCLAW_GATEWAY_TOKEN", "")
        if gw_token:
            print("==> Paperclip agents")
            wire_paperclip(gw_token, args.dry_run)
        else:
            print("WARN: OPENCLAW_GATEWAY_TOKEN missing — skip Paperclip")

    print("Done. Run verify-ghl-isolation.py and restart openclaw-gateway when ready.")


if __name__ == "__main__":
    main()
