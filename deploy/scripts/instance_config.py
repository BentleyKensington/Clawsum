#!/usr/bin/env python3
"""Instance settings from .env — no hardcoded IDs in the template repo."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"

_cache: dict[str, str] | None = None


def load_env() -> dict[str, str]:
    global _cache
    if _cache is not None:
        return _cache
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        out.setdefault(k, v)
    _cache = out
    return out


def get(key: str, default: str = "") -> str:
    return load_env().get(key, default).strip() or default


def require(key: str) -> str:
    val = get(key)
    if not val:
        raise SystemExit(f"Missing required env: {key} (set in /docker/clawsum/.env)")
    return val


def paperclip_company_id() -> str:
    return require("PAPERCLIP_COMPANY_ID")


def telegram_report_chat_id() -> str:
    return require("TELEGRAM_REPORT_CHAT_ID")


def telegram_paperclip_group_id() -> str:
    return require("TELEGRAM_PAPERCLIP_GROUP_ID")
