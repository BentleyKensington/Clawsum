#!/usr/bin/env python3
"""Create Paperclip epic/task for Media Phase 0 (assignee Clawsum Media)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:3100/api"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in Path("/docker/clawsum/.env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def req(method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(
        f"{API.rstrip('/')}/{path.lstrip('/')}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main() -> int:
    env = load_env()
    cid = env["PAPERCLIP_COMPANY_ID"]
    code, agents = req("GET", f"/companies/{cid}/agents")
    if not isinstance(agents, list):
        print("agents fail", code)
        return 1
    media = next(
        (
            a
            for a in agents
            if (a.get("adapterConfig") or {}).get("agentId") == "media"
            or a.get("name") == "Clawsum Media"
        ),
        None,
    )
    if not media:
        print("Clawsum Media agent missing — run wire-paperclip-clawsum.py first")
        return 1

    body = {
        "title": "Media Production Agent — Phase 0 (ingest + Whisper ready)",
        "description": """## Goal
Stand up Media OS Phase 0 on VPS path (Boss local GPU/Ollama stack deferred).

## Acceptance
1. Watch folder `/docker/clawsum/data/media/inbox` documented and writable
2. `ffmpeg` / `ffprobe` / `yt-dlp` installed; `FFMPEG_BIN` set in env
3. `media-ingest.py --watch … --dry-run` succeeds
4. Skills loaded: media-ingest-watch, media-transcribe, media-package-seo
5. PAPERCLIP_API_URL for gateway = `http://host.docker.internal:3102/api`
6. Do **not** publish (Tier 2). Do **not** require local Ollama yet.

## Out of scope
- Boss local stack / local LLM install (deferred)
- YouTube upload
- Resolve / ComfyUI / Velorn

## Cell
media-production
""",
        "status": "todo",
        "priority": "high",
        "assigneeAgentId": media["id"],
    }
    code, issue = req("POST", f"/companies/{cid}/issues", body)
    print("create", code)
    if isinstance(issue, dict):
        print("ISSUE", issue.get("identifier"), issue.get("id"), issue.get("status"))
        return 0
    print(issue)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
