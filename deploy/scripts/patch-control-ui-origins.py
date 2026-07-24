#!/usr/bin/env python3
"""Allow Control UI from Traefik HTTPS URL and local SSH tunnels."""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG = Path("/docker/clawsum/data/.openclaw/openclaw.json")
ENV_FILE = Path("/docker/clawsum/.env")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    out.update({k: v for k, v in os.environ.items() if k not in out or not out.get(k)})
    return out


def main() -> None:
    env = load_env()
    host = env.get("TRAEFIK_HOST", "srv.example.com")
    openclaw_ui = env.get("OPENCLAW_UI_HOST", f"openclaw.{host}")
    port = env.get("OPENCLAW_GATEWAY_PORT", "48166")
    origins = [
        f"https://{openclaw_ui}",
        f"https://clawsum.{host}",
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
        "http://127.0.0.1:18789",
        "http://localhost:18789",
    ]
    # Dedupe preserving order
    seen: set[str] = set()
    origins = [o for o in origins if not (o in seen or seen.add(o))]

    cfg = json.loads(CONFIG.read_text())
    gw = cfg.setdefault("gateway", {})
    gw.setdefault("controlUi", {})["allowedOrigins"] = origins
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    CONFIG.chmod(0o600)
    try:
        os.chown(CONFIG, 1000, 1000)
    except OSError:
        pass
    print("gateway.controlUi.allowedOrigins:")
    for o in origins:
        print(f"  - {o}")


if __name__ == "__main__":
    main()
