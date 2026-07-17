#!/usr/bin/env python3
"""
Resume agents after Boss has updated tasks (does NOT auto-start heartbeats).

Usage:
  python3 paperclip-resume-work.py              # unpause agents only
  python3 paperclip-resume-work.py --enable-heartbeats
"""
from __future__ import annotations

import argparse
import json
import urllib.request

API = "http://127.0.0.1:3100/api"
COMPANY = ""


def api(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body else None
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
    p = argparse.ArgumentParser()
    p.add_argument(
        "--enable-heartbeats",
        action="store_true",
        help="Also run enable-paperclip-heartbeats.py",
    )
    args = p.parse_args()

    code, agents = api("GET", f"companies/{COMPANY}/agents")
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        aid = agent["id"]
        name = agent.get("name", aid)
        if name == "Clawsum Hermes":
            status = "idle"
        else:
            status = "idle"
        api("PATCH", f"agents/{aid}", {"status": status})
        print(f"  {name}: status={status}")

    if args.enable_heartbeats:
        import subprocess
        import sys
        from pathlib import Path

        script = Path("/docker/clawsum/scripts/enable-paperclip-heartbeats.py")
        subprocess.run([sys.executable, str(script)], check=False)
    else:
        print("Heartbeats still OFF. Move approved issues to todo, then --enable-heartbeats.")


if __name__ == "__main__":
    main()
