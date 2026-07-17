#!/usr/bin/env python3
"""
Fix Paperclip → OpenClaw execution path:
- Gateway WS URL with /ws path
- Re-patch all openclaw_gateway agents from .env token
- Protocol v4 patch in container
- Unblock + set todo on an issue (optional)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl  # noqa: E402

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
    return out


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
            payload = json.loads(raw) if raw else {"error": e.reason}
        except json.JSONDecodeError:
            payload = {"error": raw}
        return e.code, payload


def gateway_ws_url() -> str:
    base = GW_HTTP.replace("https://", "wss://").replace("http://", "ws://").rstrip("/")
    if not base.endswith("/ws"):
        base = base + "/ws"
    return base


def openclaw_adapter(
    agent_id: str, gw_token: str, device_private_key_pem: str | None = None
) -> dict:
    cfg = {
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
        # Persisted device + one-time approve beats token-only WS scope limits.
        "disableDeviceAuth": False,
        "autoPairOnFirstConnect": False,
        "scopes": [
            "operator.admin",
            "operator.read",
            "operator.write",
            "operator.pairing",
        ],
    }
    if device_private_key_pem:
        cfg["devicePrivateKeyPem"] = device_private_key_pem
    return cfg


def hermes_openclaw_adapter(gw_token: str, device_pem: str | None = None) -> dict:
    """Hermes via OpenClaw admin session — uses Codex (ChatGPT Plus), not API-only hermes_local."""
    cfg = openclaw_adapter("admin", gw_token, device_pem)
    cfg["sessionKey"] = "paperclip:hermes"
    cfg["waitTimeoutMs"] = 600000
    cfg["timeoutSec"] = 600
    return cfg


def patch_protocol() -> None:
    script = ROOT / "scripts/fix-paperclip-openclaw-protocol.sh"
    if script.exists():
        subprocess.run(["bash", str(script)], check=False)


def find_shared_device_pem(agents: list) -> str | None:
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        pem = (agent.get("adapterConfig") or {}).get("devicePrivateKeyPem")
        if pem and "BEGIN PRIVATE KEY" in pem:
            return pem
    return None


def patch_agents(gw_token: str) -> None:
    code, agents = api("GET", f"companies/{COMPANY_ID}/agents")
    if code != 200:
        raise SystemExit(f"GET agents failed: {code} {agents}")
    shared_pem = find_shared_device_pem(agents if isinstance(agents, list) else [])
    if shared_pem:
        print("Using shared devicePrivateKeyPem across openclaw_gateway agents")
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        name = agent.get("name", "")
        aid = agent["id"]
        adapter_type = agent.get("adapterType")
        if name == "Clawsum Hermes":
            runtime = agent.get("runtimeConfig") or {}
            body = {
                "adapterType": "openclaw_gateway",
                "adapterConfig": hermes_openclaw_adapter(gw_token, shared_pem),
                "status": "idle",
                "runtimeConfig": {
                    **runtime,
                    "heartbeat": {
                        **(runtime.get("heartbeat") or {}),
                        "enabled": False,
                    },
                },
            }
            code, res = api("PATCH", f"agents/{aid}", body)
            print(f"Hermes -> openclaw_gateway (Codex), heartbeat OFF: {code}")
            continue
        if adapter_type != "openclaw_gateway":
            continue
        oc_id = ghl.paperclip_name_to_openclaw_id().get(name)
        if not oc_id:
            continue
        body = {
            "adapterConfig": openclaw_adapter(oc_id, gw_token, shared_pem),
            "status": "idle",
        }
        code, res = api("PATCH", f"agents/{aid}", body)
        print(f"{name}: PATCH adapter {code} url={gateway_ws_url()}")


def unblock_issue(issue_id: str | None) -> None:
    if not issue_id:
        code, issues = api("GET", f"companies/{COMPANY_ID}/issues?status=blocked")
        if code != 200 or not isinstance(issues, list) or not issues:
            return
        issue_id = issues[0]["id"]
    code, res = api(
        "PATCH",
        f"issues/{issue_id}",
        {"status": "todo", "assigneeAgentId": None},
    )
    print(f"Unblock issue {issue_id}: {code}")
    # Re-assign admin
    code, agents = api("GET", f"companies/{COMPANY_ID}/agents")
    admin_id = None
    for a in agents if isinstance(agents, list) else []:
        if a.get("name") == "Clawsum Admin":
            admin_id = a["id"]
            break
    if admin_id:
        code, res = api(
            "PATCH",
            f"issues/{issue_id}",
            {"status": "todo", "assigneeAgentId": admin_id},
        )
        print(f"Re-assign Admin: {code}")


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--issue-id", help="Blocked issue UUID to reset to todo")
    p.add_argument("--skip-protocol", action="store_true")
    args = p.parse_args()

    env = load_env()
    token = env.get("OPENCLAW_GATEWAY_TOKEN", "")
    if not token:
        raise SystemExit("OPENCLAW_GATEWAY_TOKEN missing in .env")

    if not args.skip_protocol:
        patch_protocol()

    patch_agents(token)
    unblock_issue(args.issue_id)
    approve = ROOT / "scripts/approve-all-paperclip-devices.py"
    if approve.exists():
        print("Approving gateway device pairings...")
        subprocess.run([sys.executable, str(approve)], check=False)
    print("Done. Wait ~5 min for heartbeat or set issue to in_progress in Boss UI.")


if __name__ == "__main__":
    main()
