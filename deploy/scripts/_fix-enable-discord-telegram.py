#!/usr/bin/env python3
"""Re-enable Discord (+ Telegram) plugins without dumping secrets."""
from __future__ import annotations

import json
from pathlib import Path

P = Path("/docker/clawsum/data/.openclaw/openclaw.json")
cfg = json.loads(P.read_text())

channels = cfg.setdefault("channels", {})
# Discord was configured enabled but plugin forced off by configure-openclaw.py
discord = channels.setdefault("discord", {})
discord["enabled"] = True
telegram = channels.setdefault("telegram", {})
telegram["enabled"] = True

plugins = cfg.setdefault("plugins", {})
entries = plugins.setdefault("entries", {})
entries["discord"] = {"enabled": True}
entries["telegram"] = {"enabled": True}
allow = set(plugins.get("allow") or [])
allow.update(["discord", "telegram", "openai", "openrouter", "anthropic", "google", "xai", "browser", "microsoft"])
plugins["allow"] = sorted(allow)

P.write_text(json.dumps(cfg, indent=2) + "\n")
P.chmod(0o600)
print("enabled discord+telegram channel+plugin")
print("discord.channel", discord.get("enabled"), "plugin", entries["discord"])
print("telegram.channel", telegram.get("enabled"), "plugin", entries["telegram"])
