#!/usr/bin/env python3
"""Copy Clawsum Admin devicePrivateKeyPem to every openclaw_gateway agent."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API = os.environ.get("PAPERCLIP_API", "http://127.0.0.1:3100/api")
COMPANY_ID = os.environ.get(
    "PAPERCLIP_COMPANY_ID", ""
)
ADMIN_NAME = "Clawsum Admin"


def api(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode()
        return resp.status, json.loads(raw) if raw else None


def main() -> None:
    _, agents = api("GET", f"companies/{COMPANY_ID}/agents")
    admin = next(a for a in agents if a.get("name") == ADMIN_NAME)
    pem = (admin.get("adapterConfig") or {}).get("devicePrivateKeyPem")
    if not pem:
        raise SystemExit("Admin has no devicePrivateKeyPem — open Boss UI once or run paperclip-fix-execution")
    for agent in agents:
        if agent.get("adapterType") != "openclaw_gateway":
            continue
        cfg = dict(agent.get("adapterConfig") or {})
        cfg["devicePrivateKeyPem"] = pem
        cfg["disableDeviceAuth"] = False
        cfg["autoPairOnFirstConnect"] = False
        code, _ = api("PATCH", f"agents/{agent['id']}", {"adapterConfig": cfg, "status": "idle"})
        print(f"{agent['name']}: {code}")


if __name__ == "__main__":
    main()
