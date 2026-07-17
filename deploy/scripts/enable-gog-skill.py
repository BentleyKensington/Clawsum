#!/usr/bin/env python3
"""Enable gog skill in openclaw.json (Gmail via gog CLI)."""
import json
from pathlib import Path

CONFIG = Path("/docker/clawsum/data/.openclaw/openclaw.json")


def main() -> None:
    cfg = json.loads(CONFIG.read_text())
    skills = cfg.setdefault("skills", {})
    entries = skills.setdefault("entries", {})
    entries["gog"] = {"enabled": True}
    # hhmail is Hostinger IMAP — disable when using Gmail API
    entries.setdefault("hhmail", {})["enabled"] = False
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    CONFIG.chmod(0o600)
    print("Enabled skills.entries.gog; disabled hhmail")


if __name__ == "__main__":
    main()
