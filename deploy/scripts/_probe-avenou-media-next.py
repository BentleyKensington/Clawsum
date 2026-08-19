#!/usr/bin/env python3
"""Probe Avenou/GHL archive Paperclip issues + API path health."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:3100/api"
PROXY = "http://127.0.0.1:3102/api"
ENV = Path("/docker/clawsum/.env")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get(url: str):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode())


env = load_env()
cid = env.get("PAPERCLIP_COMPANY_ID", "97112442-5ced-44f2-afb8-dd5ee90145b9")

for label, base in (("local3100", API), ("proxy3102", PROXY)):
    try:
        h = get(f"{base}/health")
        print(f"{label}_health OK", h if isinstance(h, dict) else type(h).__name__)
    except Exception as e:
        print(f"{label}_health FAIL", type(e).__name__, e)

# CLA-59 specifically
print("\n=== CLA-59 / CLA-61 / CLA-62 ===")
for ident in ("CLA-59", "CLA-61", "CLA-62", "CLA-50", "CLA-58"):
    try:
        issues = get(f"{API}/companies/{cid}/issues?q={ident}")
        if not isinstance(issues, list):
            issues = issues.get("issues") or issues.get("data") or []
        hit = next((i for i in issues if i.get("identifier") == ident), None)
        if not hit and issues:
            hit = issues[0]
        if hit:
            print(
                hit.get("identifier"),
                hit.get("status"),
                (hit.get("title") or "")[:70],
                "assignee=",
                (hit.get("assigneeAgentId") or hit.get("assignee") or "")[:40],
            )
        else:
            print(ident, "NOT_FOUND")
    except Exception as e:
        print(ident, "ERR", e)

# Avenou-ish open issues
print("\n=== open Avenou/archive-ish ===")
needles = ("aven", "ave", "archive", "ghl-ave", "activity")
for status in ("blocked", "in_progress", "todo", "backlog", "in_review"):
    try:
        issues = get(f"{API}/companies/{cid}/issues?status={status}")
        if not isinstance(issues, list):
            issues = issues.get("issues") or issues.get("data") or []
    except Exception as e:
        print(status, "ERR", e)
        continue
    hits = []
    for i in issues:
        blob = " ".join(
            [
                str(i.get("identifier") or ""),
                str(i.get("title") or ""),
                str(i.get("description") or "")[:200],
            ]
        ).lower()
        if any(n in blob for n in needles):
            hits.append(i)
    print(f"{status}: total={len(issues)} avenish={len(hits)}")
    for i in hits[:12]:
        print(
            " ",
            i.get("identifier"),
            i.get("status"),
            (i.get("title") or "")[:75],
        )

# gateway path test
print("\n=== gateway PAPERCLIP_API_URL ===")
import subprocess

proc = subprocess.run(
    ["docker", "exec", "clawsum-openclaw-gateway-1", "printenv", "PAPERCLIP_API_URL"],
    capture_output=True,
    text=True,
)
print((proc.stdout or "").strip() or "(unset)")
proc2 = subprocess.run(
    [
        "docker",
        "exec",
        "clawsum-openclaw-gateway-1",
        "sh",
        "-c",
        "curl -sS -m 5 -o /dev/null -w '%{http_code}' http://host.docker.internal:3102/api/health",
    ],
    capture_output=True,
    text=True,
)
print("gateway->3102", (proc2.stdout or "").strip(), (proc2.stderr or "")[-120:])
