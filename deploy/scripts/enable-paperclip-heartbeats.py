#!/usr/bin/env python3
"""Enable Paperclip heartbeats on all Clawsum company agents."""
import json
import os
import urllib.error
import urllib.request

API = os.environ.get("PAPERCLIP_API", "http://127.0.0.1:3100/api")
COMPANY_ID = os.environ.get(
    "PAPERCLIP_COMPANY_ID", ""
)
INTERVAL_MS = int(os.environ.get("PAPERCLIP_HEARTBEAT_MS", "300000"))  # 5 min


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
                "heartbeat": {
                    **heartbeat,
                    "enabled": True,
                    "intervalMs": heartbeat.get("intervalMs") or INTERVAL_MS,
                },
            }
        }
        code, res = api("PATCH", f"agents/{aid}", body)
        status = "ok" if code == 200 else res
        print(f"{name}: PATCH {code} -> {status}")


if __name__ == "__main__":
    main()
