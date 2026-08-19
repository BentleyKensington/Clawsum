#!/usr/bin/env python3
"""Seed Discord HQ channels with short purpose posts so they are not empty."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("/docker/clawsum")
ENV = ROOT / ".env"
MAP = ROOT / "data" / "discord-hq-map.json"

SEED = {
    "start_here": "Clawsum HQ is live. Preferred mobile ops channel. Alerts dual-write with Telegram until verified.",
    "rules": "No secrets in chat. Approvals stay in Boss UI (boss.clawsum.com). Keep channel traffic on-purpose.",
    "boss_alerts": "Urgent alerts land here (OAuth, Grafana, outages).",
    "boss_desk": "Talk to Clawsum Admin here — free-respond, no @mention required. Say hi to test 2-way.",
    "approvals": "Approval links / reminders. Decide in Boss UI: https://boss.clawsum.com",
    "ops_digest": "7am global report + reminders digest.",
    "gmail": "Inbox heat / needs_boss summaries (no raw email bodies).",
    "monitoring": "Infra notes + Grafana: https://grafana.clawsum.com",
    "jarvis": "Jarvis / Admin face on Discord. Free-respond — say hi.",
    "admin": "Admin agent channel. Free-respond.",
    "paperclip": "Paperclip board hygiene agent.",
    "coding": "Coding / VPS agent.",
    "data": "Data / ETL agent.",
    "ghl": "GHL template agent (instance overlays may differ).",
    "comms": "Comms drafts (send = Tier 2 approval).",
    "research": "Research agent.",
    "closebot": "CloseBot operator lane. Use for lead-routing and CloseBot API work.",
    "printful": "Printful lane. Use for fulfillment, product, and merchant support tasks.",
    "shopify": "Shopify lane. Use for storefront, orders, and commerce operations.",
    "seo_aeo_geo": "SEO / AEO / GEO lane. Use for organic search, answer engine, and geo visibility work.",
    "meta_ads": "Meta Ads lane. Use for Facebook and Instagram ads operations.",
    "acceptai": "AcceptAI lane. Use for AcceptAI / FastBuy commerce work.",
    "calendar": "Calendar lane. Use for calendar hygiene, invites, and scheduling ops.",
    "slack_avenou": "Slack Avenou lane. Use for Avenou Slack comms and workflows.",
    "vocalitic": "Vocalitic product lane — codebase v1m12, dashboard, SSH observations.",
    "llm_lab": "LLM Lab — free vs paid models, Deepgram/NVIDIA watch.",
    "vapi": "VAPI org lane — assistants, calls, numbers.",
    "sellthebizfast": "SellTheBizFast acquisitions — buy box, CIM, DD questions.",
    "rocco": "Rocco Secure — sentry, official Ring only, no exploits.",
    "wins": "Shipped / closed — short notes only.",
    "bot_test": "Smoke tests only.",
}


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, _, v = raw.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def send(token: str, channel_id: str, content: str) -> None:
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        data=json.dumps({"content": content}).encode(),
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "ClawsumHQ/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def main() -> int:
    env = load_env()
    token = env.get("DISCORD_BOT_TOKEN") or ""
    data = json.loads(MAP.read_text(encoding="utf-8"))
    channels = data.get("channels") or {}
    ok = fail = 0
    for key, text in SEED.items():
        ch = channels.get(key) or {}
        cid = ch.get("id")
        if not cid or ch.get("type") not in (0, None):
            # skip categories / voice / forum for simple seed
            if ch.get("type") not in (0,):
                continue
        if not cid:
            continue
        try:
            send(token, str(cid), text)
            ok += 1
            print(f"seeded #{ch.get('name', key)}")
            time.sleep(0.35)
        except urllib.error.HTTPError as e:
            fail += 1
            print(f"FAIL #{ch.get('name', key)}: {e.code} {e.read().decode()[:120]}")
    print(f"done ok={ok} fail={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
