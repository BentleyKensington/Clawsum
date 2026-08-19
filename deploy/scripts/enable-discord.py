#!/usr/bin/env python3
"""Enable OpenClaw Discord channel plugin (2-way)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

CONFIG = Path("/docker/clawsum/data/.openclaw/openclaw.json")
ENV = Path("/docker/clawsum/.env")
MAP = Path("/docker/clawsum/data/discord-hq-map.json")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            k, _, v = raw.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> int:
    if not CONFIG.exists():
        raise SystemExit(f"missing {CONFIG}")
    env = load_env()
    token = (env.get("DISCORD_BOT_TOKEN") or "").strip()
    guild = (env.get("DISCORD_GUILD_ID") or "").strip()
    boss_user = (env.get("DISCORD_BOSS_USER_ID") or "").strip()
    if not token:
        raise SystemExit("DISCORD_BOT_TOKEN missing in .env")
    if not guild:
        raise SystemExit("DISCORD_GUILD_ID missing — run discord-provision-hq.py first")

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    plugins = cfg.setdefault("plugins", {})
    allow = plugins.setdefault("allow", [])
    if "discord" not in allow:
        allow.append("discord")
    plugins.setdefault("entries", {})["discord"] = {"enabled": True}

    # Channel allowlist from HQ map when present
    channel_map: dict[str, dict] = {}
    if MAP.exists():
        data = json.loads(MAP.read_text(encoding="utf-8"))
        for key, ch in (data.get("channels") or {}).items():
            if not isinstance(ch, dict):
                continue
            if ch.get("type") in (0, 15) and ch.get("id"):
                # free-respond in agent + boss desk; mention required elsewhere optional
                require = key not in (
                    "boss_desk",
                    "jarvis",
                    "admin",
                    "paperclip",
                    "coding",
                    "data",
                    "ghl",
                    "comms",
                    "research",
                )
                channel_map[str(ch["id"])] = {
                    "enabled": True,
                    "requireMention": require,
                }

    guild_cfg: dict = {
        "requireMention": False,
        "users": [boss_user] if boss_user else ["*"],
    }
    if channel_map:
        channel_map["*"] = {"enabled": True, "requireMention": True}
        guild_cfg["channels"] = channel_map

    discord_cfg = {
        "enabled": True,
        "token": {"source": "env", "provider": "default", "id": "DISCORD_BOT_TOKEN"},
        "dmPolicy": "allowlist",
        "allowFrom": [boss_user] if boss_user else [],
        "groupPolicy": "allowlist",
        "guilds": {guild: guild_cfg},
    }
    if not boss_user:
        print(
            "WARN: DISCORD_BOSS_USER_ID unset — set your Discord user ID for DM allowlist",
            flush=True,
        )

    cfg.setdefault("channels", {})["discord"] = discord_cfg
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print("discord enabled in openclaw.json")
    print("Restart gateway: cd /docker/clawsum && docker compose restart openclaw-gateway")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
