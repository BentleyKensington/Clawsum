#!/usr/bin/env python3
"""Add Dispo Dudes to VPS ghl-accounts.json + .env (no secrets printed)."""
from __future__ import annotations

import json
import secrets
from pathlib import Path

CFG = Path("/docker/clawsum/config/ghl-accounts.json")
ENV = Path("/docker/clawsum/.env")

ACCOUNT = {
    "slug": "dispo-dudes",
    "id": "ghl-dispo-dudes",
    "display_name": "Dispo Dudes",
    "schema_prefix": "dispo_dudes",
    "obsidian_folder": "DISPO-DUDES",
    "paperclip_name": "Clawsum GHL — Dispo Dudes",
    "telegram_needles": ["dispo dudes", "dispo-dudes", "ghl dispo", "dispodeudes"],
    "env_pit": "GHL_DISPO_DUDES_PIT",
    "env_location": "GHL_DISPO_DUDES_LOCATION_ID",
    "env_db_password": "GHL_DISPO_DUDES_DB_PASSWORD",
    "mcp_server": "ghl-dispo-dudes",
    "identity_name": "Dispo Dudes",
    "identity_emoji": "🤝",
}


def upsert_account() -> None:
    data = json.loads(CFG.read_text())
    accs = data.setdefault("accounts", [])
    for i, a in enumerate(accs):
        if a.get("slug") == "dispo-dudes" or a.get("id") == "ghl-dispo-dudes":
            accs[i] = {**a, **ACCOUNT}
            CFG.write_text(json.dumps(data, indent=2) + "\n")
            print("Updated existing Dispo Dudes account in ghl-accounts.json")
            return
    accs.append(ACCOUNT)
    CFG.write_text(json.dumps(data, indent=2) + "\n")
    print("Added Dispo Dudes account to ghl-accounts.json")


def ensure_env() -> None:
    text = ENV.read_text(encoding="utf-8") if ENV.exists() else ""
    lines = text.splitlines()
    keys = {
        "GHL_DISPO_DUDES_PIT": "",
        "GHL_DISPO_DUDES_LOCATION_ID": "",
        "GHL_DISPO_DUDES_DB_PASSWORD": secrets.token_urlsafe(18),
    }
    have = set()
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            have.add(line.split("=", 1)[0].strip())
    added = []
    for k, v in keys.items():
        if k not in have:
            lines.append(f"{k}={v}")
            added.append(k)
    if added:
        ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("Added env keys: " + ", ".join(added))
    else:
        print("Env keys already present")


if __name__ == "__main__":
    upsert_account()
    ensure_env()
