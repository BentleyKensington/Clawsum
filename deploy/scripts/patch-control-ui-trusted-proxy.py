#!/usr/bin/env python3
"""
Enable OpenClaw trusted-proxy auth for Control UI behind Traefik ops portal.

Run after setup-ops-portal-traefik.sh so Traefik sends X-Forwarded-User.
Requires OpenClaw 2026.6.10+ with trusted-proxy support.

  python3 /docker/clawsum/scripts/patch-control-ui-trusted-proxy.py
  cd /docker/clawsum && docker compose restart openclaw-gateway
"""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG = Path("/docker/clawsum/data/.openclaw/openclaw.json")
ENV_FILE = Path("/docker/clawsum/.env")

# Traefik on host network → gateway sees Docker bridge gateway or host
DEFAULT_TRUSTED = ["172.17.0.1", "172.18.0.1", "127.0.0.1", "::1"]


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> None:
    env = load_env()
    if env.get("OPENCLAW_TRUSTED_PROXY", "true").lower() in ("0", "false", "no"):
        print("SKIP: OPENCLAW_TRUSTED_PROXY=false")
        return

    user_header = env.get("OPENCLAW_TRUSTED_PROXY_USER_HEADER", "x-forwarded-user")
    allow_users = [u.strip() for u in env.get("BOSS_OPS_AUTH_USER", "boss").split(",") if u.strip()]
    extra = [x.strip() for x in env.get("OPENCLAW_TRUSTED_PROXIES", "").split(",") if x.strip()]
    trusted = list(dict.fromkeys(DEFAULT_TRUSTED + extra))

    cfg = json.loads(CONFIG.read_text())
    gw = cfg.setdefault("gateway", {})
    gw["bind"] = gw.get("bind") or "lan"
    gw["trustedProxies"] = trusted

    auth = gw.setdefault("auth", {})
    auth["mode"] = "trusted-proxy"
    tp = auth.setdefault("trustedProxy", {})
    tp["userHeader"] = user_header
    tp["allowLoopback"] = True
    if allow_users:
        tp["allowUsers"] = allow_users

    gw.setdefault("controlUi", {})
    # Origins patched separately by patch-control-ui-origins.py

    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    CONFIG.chmod(0o600)
    try:
        os.chown(CONFIG, 1000, 1000)
    except OSError:
        pass

    print("gateway.auth.mode = trusted-proxy")
    print(f"gateway.trustedProxies = {trusted}")
    print(f"gateway.auth.trustedProxy.userHeader = {user_header}")
    print(f"gateway.auth.trustedProxy.allowUsers = {allow_users}")
    print("Restart: cd /docker/clawsum && docker compose restart openclaw-gateway")


if __name__ == "__main__":
    main()
