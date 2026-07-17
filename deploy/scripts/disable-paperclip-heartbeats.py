#!/usr/bin/env python3
"""Turn OFF Paperclip heartbeats (stop auto agent runs until Boss is ready)."""
import json
import os
import urllib.error
import urllib.request

API = os.environ.get("PAPERCLIP_API", "http://127.0.0.1:3100/api")
COMPANY_ID = os.environ.get(
    "PAPERCLIP_COMPANY_ID", ""
)


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
            return e.code, json.loads(raw) if raw else {"error": raw}
        except json.JSONDecodeError:
            return e.code, {"error": raw}


def main() -> None:
    code, agents = api("GET", f"companies/{COMPANY_ID}/agents")
    if code != 200:
        raise SystemExit(f"GET agents failed: {code} {agents}")
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        aid = agent["id"]
        name = agent.get("name", aid)
        runtime = agent.get("runtimeConfig") or {}
        heartbeat = runtime.get("heartbeat") or {}
        body = {
            "runtimeConfig": {
                **runtime,
                "heartbeat": {**heartbeat, "enabled": False},
            }
        }
        code, res = api("PATCH", f"agents/{aid}", body)
        print(f"{name}: heartbeat OFF ({code})")


if __name__ == "__main__":
    main()
