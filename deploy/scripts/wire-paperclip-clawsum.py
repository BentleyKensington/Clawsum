#!/usr/bin/env python3
"""Wire Clawsum company + OpenClaw gateway agents + Hermes secret in Paperclip (local_trusted)."""
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
GW_HTTP = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:48166")


def gateway_ws_url(http_base: str) -> str:
    ws = http_base.replace("https://", "wss://").replace("http://", "ws://").rstrip("/")
    if not ws.endswith("/ws"):
        ws = ws + "/ws"
    return ws


GW_WS = gateway_ws_url(GW_HTTP)

COMPANY_NAME = "Clawsum"
COMPANY_DESC = "Multi-agent operations platform for Bentley Kensington."

AGENTS = [
    ("Clawsum Admin", "admin", "ceo", "CEO / liaison — triage, delegate, status."),
    ("Clawsum Coding", "coding", "engineer", "Engineering — repos, deploy, scripts."),
    ("Clawsum Data", "data", "engineer", "Data — scrapers, reports, Postgres."),
    ("Clawsum RE", "realestate", "engineer", "Real estate — comps, deals DB."),
]
for _name, _oc_id, _cap in ghl.paperclip_agents():
    AGENTS.append((_name, _oc_id, "engineer", _cap))
AGENTS.extend(
    [
        ("Clawsum Comms", "comms", "engineer", "Communications — drafts, campaigns."),
        ("Clawsum Research", "research", "researcher", "Research — web, synthesis."),
        ("Clawsum Planning", "planning", "pm", "Planning — roadmaps, tasks."),
        ("Clawsum Paperclip", "paperclip", "pm", "Orchestration liaison."),
        ("Clawsum Hermes", "hermes", "engineer", "Long-running jobs via Hermes."),
    ]
)


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENV_FILE.exists():
        return out
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
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw) if raw else {"error": e.reason}
        except json.JSONDecodeError:
            payload = {"error": raw or str(e)}
        return e.code, payload


def patch_config() -> None:
    p = ROOT / "paperclip-data/instances/default/config.json"
    c = json.loads(p.read_text())
    c.setdefault("server", {})
    c["server"].update(
        {
            "host": "127.0.0.1",
            "bind": "loopback",
            "port": 3100,
            "deploymentMode": "local_trusted",
        }
    )
    p.write_text(json.dumps(c, indent=2) + "\n")
    print("patched config.json (loopback)")


def ensure_company() -> str:
    code, companies = api("GET", "companies")
    if code != 200:
        print(f"GET companies -> {code}: {companies}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(companies, list):
        companies = []
    for c in companies:
        if c.get("name") == COMPANY_NAME or c.get("slug") == "clawsum":
            cid = c["id"]
            print(f"company exists: {cid}")
            return cid

    code, created = api(
        "POST",
        "companies",
        {
            "name": COMPANY_NAME,
            "description": COMPANY_DESC,
            "budgetMonthlyCents": 500_000,
            "issuePrefix": "CLW",
        },
    )
    if code not in (200, 201):
        print(f"POST companies -> {code}: {created}", file=sys.stderr)
        sys.exit(1)
    cid = created["id"]
    print(f"created company: {cid}")
    return cid


def ensure_secret(company_id: str, gw_token: str) -> None:
    code, secrets = api("GET", f"companies/{company_id}/secrets")
    if code != 200:
        print(f"GET secrets -> {code}: {secrets}", file=sys.stderr)
        return
    names = {s.get("name") for s in secrets if isinstance(s, dict)}
    if "openclaw_gateway_token" in names:
        print("secret openclaw_gateway_token already exists")
        return
    code, res = api(
        "POST",
        f"companies/{company_id}/secrets",
        {
            "name": "openclaw_gateway_token",
            "value": gw_token,
            "description": "OpenClaw gateway bearer token",
        },
    )
    print(f"POST secret -> {code}: {res}")


def openclaw_adapter(agent_id: str, gw_token: str) -> dict:
    return {
        "url": GW_WS,
        "agentId": agent_id,
        "sessionKeyStrategy": "fixed",
        "sessionKey": f"paperclip:{agent_id}",
        "headers": {
            "authorization": f"Bearer {gw_token}",
            "x-openclaw-token": gw_token,
        },
        "timeoutSec": 300,
        "waitTimeoutMs": 300000,
        # Loopback VPS: gateway token is enough; avoids endless "pairing required" on new device IDs.
        "disableDeviceAuth": True,
        "autoPairOnFirstConnect": False,
        # Match gateway token capabilities (operator.admin); extra scopes cause agent 403.
        "scopes": ["operator.admin"],
    }


def hermes_openclaw_adapter(gw_token: str) -> dict:
    # Hermes via OpenClaw (admin + paperclip:hermes session) → Codex / ChatGPT Plus.
    # Boss must still explicitly assign Clawsum Hermes (see HERMES-POLICY.md).
    cfg = openclaw_adapter("admin", gw_token)
    cfg["sessionKey"] = "paperclip:hermes"
    cfg["timeoutSec"] = 600
    cfg["waitTimeoutMs"] = 600000
    return cfg


def ensure_agents(company_id: str, gw_token: str) -> None:
    code, agents = api("GET", f"companies/{company_id}/agents")
    if code != 200:
        print(f"GET agents -> {code}: {agents}", file=sys.stderr)
        sys.exit(1)
    by_name = {a.get("name"): a for a in agents if isinstance(a, dict)}

    for name, oc_id, role, capabilities in AGENTS:
        if name in by_name:
            existing = by_name[name]
            aid = existing["id"]
            if oc_id == "hermes":
                cfg = hermes_openclaw_adapter(gw_token)
                body = {
                    "adapterType": "openclaw_gateway",
                    "adapterConfig": cfg,
                    "status": "idle",
                }
            elif existing.get("adapterType") == "openclaw_gateway":
                body = {"adapterConfig": openclaw_adapter(oc_id, gw_token), "status": "idle"}
            else:
                print(f"agent exists: {name}")
                continue
            code, res = api("PATCH", f"agents/{aid}", body)
            print(f"patch {name} -> {code}")
            continue
        adapter_type = "openclaw_gateway"
        adapter_config = (
            hermes_openclaw_adapter(gw_token)
            if oc_id == "hermes"
            else openclaw_adapter(oc_id, gw_token)
        )
        body = {
            "name": name,
            "role": role,
            "title": name.replace("Clawsum ", ""),
            "capabilities": capabilities,
            "adapterType": adapter_type,
            "adapterConfig": adapter_config,
            "budgetMonthlyCents": 50_000,
        }
        code, res = api("POST", f"companies/{company_id}/agents", body)
        print(f"hire {name} ({adapter_type}) -> {code}: {res if code not in (200, 201) else res.get('id', res)}")


def gateway_health() -> None:
    health_url = GW_HTTP.rstrip("/") + "/healthz"
    try:
        with urllib.request.urlopen(health_url, timeout=10) as resp:
            print(f"gateway healthz: {resp.status}")
    except Exception as e:
        print(f"gateway healthz FAILED: {e}", file=sys.stderr)


def main() -> None:
    env = load_env()
    gw_token = env.get("OPENCLAW_GATEWAY_TOKEN", "")
    if not gw_token:
        print("ERROR: OPENCLAW_GATEWAY_TOKEN missing in .env", file=sys.stderr)
        sys.exit(1)

    patch_config()
    code, health = api("GET", "health")
    print(f"health {code}: {json.dumps(health)}")
    gateway_health()

    company_id = ensure_company()
    ensure_secret(company_id, gw_token)
    ensure_agents(company_id, gw_token)

    # Approve pending device pairings on gateway
    try:
        out = subprocess.run(
            [
                "docker",
                "exec",
                "clawsum-openclaw-gateway-1",
                "node",
                "dist/index.js",
                "devices",
                "list",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        print("devices list:", out.stdout or out.stderr)
        if "pending" in (out.stdout or "").lower():
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "clawsum-openclaw-gateway-1",
                    "node",
                    "dist/index.js",
                    "devices",
                    "approve",
                    "--latest",
                ],
                check=False,
                timeout=30,
            )
            print("approved latest device")
    except Exception as e:
        print(f"device pairing skipped: {e}")


if __name__ == "__main__":
    main()
