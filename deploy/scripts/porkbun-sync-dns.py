#!/usr/bin/env python3
"""
Sync clawsum.com DNS at Porkbun to the Clawsum VPS map.

Requires env (never commit):
  PORKBUN_API_KEY
  PORKBUN_SECRET_KEY
  CLAWSUM_VPS_IP   (default 76.13.97.82)

Optional:
  PORKBUN_DOMAIN=clawsum.com
  DRY_RUN=1
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

API = "https://api.porkbun.com/api/json/v3"
DOMAIN = os.environ.get("PORKBUN_DOMAIN", "clawsum.com")
IP = os.environ.get("CLAWSUM_VPS_IP", "76.13.97.82")
DRY = os.environ.get("DRY_RUN", "").strip() in ("1", "true", "yes")

# Subdomain labels (empty string = apex). www included.
A_HOSTS = [
    "",  # apex
    "www",
    "hermes",
    "boss",
    "openclaw",
    "grafana",
    "login",
    "connect",
    "api",
    "mail",
]

# Parking / catch-alls that block custom hosts
DELETE_IF_MATCH = [
    ("ALIAS", DOMAIN, "uixie.porkbun.com"),
    ("CNAME", f"*.{DOMAIN}", "uixie.porkbun.com"),
    ("CNAME", f"www.{DOMAIN}", "uixie.porkbun.com"),
]


def auth_body(**extra):
    key = os.environ.get("PORKBUN_API_KEY", "").strip()
    secret = os.environ.get("PORKBUN_SECRET_KEY", "").strip()
    if not key or not secret:
        raise SystemExit("Set PORKBUN_API_KEY and PORKBUN_SECRET_KEY")
    body = {"apikey": key, "secretapikey": secret}
    body.update(extra)
    return body


def api(path: str, **extra) -> dict:
    data = json.dumps(auth_body(**extra)).encode()
    req = urllib.request.Request(
        f"{API}/{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def fqdn(name: str) -> str:
    return DOMAIN if not name else f"{name}.{DOMAIN}"


def main() -> None:
    ping = api("ping")
    if ping.get("status") != "SUCCESS":
        raise SystemExit(f"Porkbun ping failed: {ping}")
    print("Porkbun ping OK")

    retrieved = api(f"dns/retrieve/{DOMAIN}")
    records = retrieved.get("records") or []
    print(f"Existing records: {len(records)}")

    # Delete parking
    for rec in records:
        rtype = rec.get("type")
        name = rec.get("name")
        content = (rec.get("content") or "").rstrip(".")
        rid = rec.get("id")
        for dtype, dname, dcontent in DELETE_IF_MATCH:
            if rtype == dtype and name == dname and content == dcontent:
                print(f"DELETE {rtype} {name} -> {content} id={rid}")
                if not DRY:
                    out = api(f"dns/delete/{DOMAIN}/{rid}")
                    print(f"  -> {out.get('status')}")
                break

    # Refresh
    records = (api(f"dns/retrieve/{DOMAIN}").get("records") or []) if not DRY else records

    def find_a(label: str):
        target = fqdn(label)
        for rec in records:
            if rec.get("type") == "A" and rec.get("name") == target:
                return rec
        return None

    for label in A_HOSTS:
        existing = find_a(label)
        display = fqdn(label)
        if existing and existing.get("content") == IP:
            print(f"OK A {display} already {IP}")
            continue
        if existing:
            print(f"EDIT A {display} {existing.get('content')} -> {IP} id={existing.get('id')}")
            if not DRY:
                out = api(
                    f"dns/edit/{DOMAIN}/{existing['id']}",
                    name=label,
                    type="A",
                    content=IP,
                    ttl="600",
                )
                print(f"  -> {out.get('status')}")
        else:
            print(f"CREATE A {display} -> {IP}")
            if not DRY:
                out = api(
                    f"dns/create/{DOMAIN}",
                    name=label,
                    type="A",
                    content=IP,
                    ttl="600",
                )
                print(f"  -> {out.get('status')} id={out.get('id')}")

    if DRY:
        print("DRY_RUN=1 — no changes applied")
    else:
        final = api(f"dns/retrieve/{DOMAIN}")
        print("--- current A/CNAME/ALIAS ---")
        for rec in final.get("records") or []:
            if rec.get("type") in ("A", "AAAA", "CNAME", "ALIAS"):
                print(f"{rec['type']:6} {rec['name']:40} {rec['content']}")


if __name__ == "__main__":
    main()
