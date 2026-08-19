#!/usr/bin/env python3
"""
Provision Clawsum Discord HQ via Bot API — roles, categories, channels, forum tags.

Prereqs (Boss does once):
  1. Create Discord Application → Bot → copy token
  2. Enable Privileged Gateway Intents: Message Content, Server Members
  3. Invite bot with permissions: Manage Channels, Manage Roles, Send Messages,
     View Channels, Read Message History, Create Public Threads, Connect (voice)
  4. Create empty server (or use existing) → enable Developer Mode → copy Server ID
  5. Put on VPS .env:
       DISCORD_BOT_TOKEN=...
       DISCORD_GUILD_ID=...

Run:
  python3 /docker/clawsum/scripts/discord-provision-hq.py
  python3 /docker/clawsum/scripts/discord-provision-hq.py --dry-run

Writes channel/role IDs into .env and data/discord-hq-map.json
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
ENV_FILE = ROOT / ".env"
MAP_FILE = ROOT / "data" / "discord-hq-map.json"
API = "https://discord.com/api/v10"

# Expanded HQ layout — ops-first, mirrors Telegram one-bot-per-channel + alerts
HQ = {
    "roles": [
        {"key": "boss", "name": "Boss", "color": 0xC9A227, "hoist": True, "mentionable": True},
        {"key": "ops", "name": "Ops", "color": 0x3B82F6, "hoist": True, "mentionable": True},
        {"key": "agent", "name": "Agent", "color": 0x22C55E, "hoist": False, "mentionable": False},
        {"key": "verified", "name": "Verified", "color": 0x64748B, "hoist": False, "mentionable": False},
    ],
    "categories": [
        {
            "key": "start",
            "name": "📋 START HERE",
            "channels": [
                {"key": "start_here", "name": "start-here", "topic": "Clawsum HQ — read first. Preferred mobile ops channel."},
                {"key": "rules", "name": "rules", "topic": "No secrets in chat. Approvals stay in Boss UI unless linked."},
            ],
        },
        {
            "key": "boss",
            "name": "🚨 BOSS",
            "channels": [
                {"key": "boss_alerts", "name": "boss-alerts", "topic": "Urgent: OAuth, Grafana firing, outages. Dual-write with Telegram until verified."},
                {"key": "boss_desk", "name": "boss-desk", "topic": "2-way with Clawsum Admin (OpenClaw). Free-respond for Boss."},
                {"key": "approvals", "name": "approvals", "topic": "Links to boss.clawsum.com Approve All — not a secret dump."},
            ],
        },
        {
            "key": "ops",
            "name": "📊 OPS",
            "channels": [
                {"key": "ops_digest", "name": "ops-digest", "topic": "7am global report + reminders digest."},
                {"key": "gmail", "name": "gmail-inbox", "topic": "Inbox heat / needs_boss summaries (no raw bodies)."},
                {"key": "monitoring", "name": "monitoring", "topic": "Grafana / Prometheus notes. Deep links to grafana.clawsum.com."},
            ],
        },
        {
            "key": "agents",
            "name": "🤖 AGENTS",
            "channels": [
                {"key": "jarvis", "name": "jarvis-hermes", "topic": "Clawsum / Hermes face — 2-way.", "agent": "hermes"},
                {"key": "admin", "name": "admin", "topic": "Admin agent — 2-way.", "agent": "admin"},
                {"key": "paperclip", "name": "paperclip", "topic": "Paperclip agent — board hygiene.", "agent": "paperclip"},
                {"key": "coding", "name": "coding", "topic": "Coding / VPS agent.", "agent": "coding"},
                {"key": "data", "name": "data", "topic": "Data / ETL agent.", "agent": "data"},
                {"key": "ghl", "name": "ghl", "topic": "GHL CRM agent.", "agent": "ghl"},
                {"key": "comms", "name": "comms", "topic": "Comms drafts (send = Tier 2).", "agent": "comms"},
                {"key": "research", "name": "research", "topic": "Research agent.", "agent": "research"},
                {"key": "closebot", "name": "closebot", "topic": "CloseBot operator lane.", "agent": "closebot"},
                {"key": "printful", "name": "printful", "topic": "Printful commerce / fulfillment lane.", "agent": "printful"},
                {"key": "shopify", "name": "shopify", "topic": "Shopify commerce lane.", "agent": "shopify"},
                {"key": "seo_aeo_geo", "name": "seo-aeo-geo", "topic": "SEO / AEO / GEO growth lane.", "agent": "seo-aeo-geo"},
                {"key": "meta_ads", "name": "meta-ads", "topic": "Facebook / Meta Ads lane.", "agent": "meta-ads"},
                {"key": "acceptai", "name": "acceptai", "topic": "AcceptAI commerce lane.", "agent": "acceptai"},
                {"key": "calendar", "name": "calendar", "topic": "Calendar ops lane.", "agent": "calendar"},
                {"key": "slack_avenou", "name": "slack-avenou", "topic": "Slack Avenou communications lane.", "agent": "slack-avenou"},
                {"key": "vocalitic", "name": "vocalitic", "topic": "Vocalitic product — v1m12, dashboard, SSH.", "agent": "vocalitic"},
                {"key": "llm_lab", "name": "llm-lab", "topic": "LLM Lab — models, Deepgram, NVIDIA.", "agent": "llm-lab"},
                {"key": "vapi", "name": "vapi", "topic": "VAPI org — assistants and calls.", "agent": "vapi"},
                {"key": "sellthebizfast", "name": "sellthebizfast", "topic": "SellTheBizFast acquisitions.", "agent": "sellthebizfast"},
                {"key": "rocco", "name": "rocco", "topic": "Rocco Secure — sentry + official Ring.", "agent": "rocco"},
            ],
        },
        {
            "key": "work",
            "name": "🗂 WORK",
            "channels": [
                {
                    "key": "tasks",
                    "name": "tasks",
                    "type": 15,  # forum
                    "topic": "Paperclip-style threads. Tags: urgent | blocked | needs-boss | done",
                    "tags": ["urgent", "blocked", "needs-boss", "done", "watch"],
                },
                {"key": "wins", "name": "wins", "topic": "Shipped / closed — short notes only."},
            ],
        },
        {
            "key": "voice",
            "name": "🔊 VOICE",
            "channels": [
                {"key": "vc_standup", "name": "Boss Standup", "type": 2},
                {"key": "vc_ops", "name": "Ops Lounge", "type": 2},
                {"key": "vc_afk", "name": "AFK", "type": 2},
            ],
        },
        {
            "key": "staff",
            "name": "🛡 STAFF",
            "private": True,
            "channels": [
                {"key": "bot_test", "name": "bot-test", "topic": "Smoke tests only."},
                {"key": "mod_log", "name": "mod-log", "topic": "Automation / audit crumbs (no secrets)."},
            ],
        },
    ],
}


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            k, _, v = raw.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    out.update({k: v for k, v in os.environ.items() if v})
    return out


def upsert_env(updates: dict[str, str]) -> None:
    lines = ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines() if ENV_FILE.exists() else []
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in updates:
                out.append(f"{k}={updates[k]}")
                seen.add(k)
                continue
        out.append(line)
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")
    try:
        os.chmod(ENV_FILE, 0o600)
    except OSError:
        pass


def api(method: str, path: str, token: str, body: dict | None = None) -> dict | list | None:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "ClawsumHQ/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} → {e.code}: {err}") from e


def rate_sleep() -> None:
    time.sleep(0.35)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--guild-id", help="Override DISCORD_GUILD_ID")
    args = ap.parse_args()

    env = load_env()
    token = (env.get("DISCORD_BOT_TOKEN") or "").strip()
    guild = (args.guild_id or env.get("DISCORD_GUILD_ID") or "").strip()
    if not token or not guild:
        print("Need DISCORD_BOT_TOKEN and DISCORD_GUILD_ID in .env", flush=True)
        print("See deploy/docs/DISCORD-HQ.md", flush=True)
        return 1

    if args.dry_run:
        print(json.dumps({"guild": guild, "layout": HQ}, indent=2))
        return 0

    me = api("GET", "/users/@me", token)
    print(f"Bot: {me.get('username')}#{me.get('discriminator', '0')} id={me.get('id')}")

    existing_roles = api("GET", f"/guilds/{guild}/roles", token) or []
    role_by_name = {r["name"]: r for r in existing_roles if isinstance(r, dict)}
    roles_out: dict[str, str] = {}

    for spec in HQ["roles"]:
        if spec["name"] in role_by_name:
            roles_out[spec["key"]] = role_by_name[spec["name"]]["id"]
            print(f"role exists: {spec['name']}")
            continue
        created = api(
            "POST",
            f"/guilds/{guild}/roles",
            token,
            {
                "name": spec["name"],
                "color": spec["color"],
                "hoist": spec["hoist"],
                "mentionable": spec["mentionable"],
            },
        )
        roles_out[spec["key"]] = created["id"]  # type: ignore[index]
        print(f"role created: {spec['name']} → {created['id']}")  # type: ignore[index]
        rate_sleep()

    existing_chs = api("GET", f"/guilds/{guild}/channels", token) or []
    ch_by_name = {
        c["name"]: c
        for c in existing_chs
        if isinstance(c, dict) and c.get("type") in (0, 2, 4, 15)
    }

    channels_out: dict[str, dict] = {}
    pos = 0
    for cat in HQ["categories"]:
        cat_id = None
        if cat["name"] in ch_by_name and ch_by_name[cat["name"]].get("type") == 4:
            cat_id = ch_by_name[cat["name"]]["id"]
            print(f"category exists: {cat['name']}")
        else:
            body: dict = {"name": cat["name"], "type": 4, "position": pos}
            created = api("POST", f"/guilds/{guild}/channels", token, body)
            cat_id = created["id"]  # type: ignore[index]
            print(f"category created: {cat['name']} → {cat_id}")
            rate_sleep()
        pos += 1
        channels_out[cat["key"]] = {"id": cat_id, "type": "category", "name": cat["name"]}

        for ch in cat["channels"]:
            ctype = int(ch.get("type") or 0)
            existing = ch_by_name.get(ch["name"])
            if existing and existing.get("type") == ctype:
                cid = existing["id"]
                print(f"  channel exists: #{ch['name']}")
            else:
                body = {
                    "name": ch["name"],
                    "type": ctype,
                    "parent_id": cat_id,
                    "topic": ch.get("topic") or "",
                }
                if ctype == 15 and ch.get("tags"):
                    body["available_tags"] = [{"name": t} for t in ch["tags"]]
                created = api("POST", f"/guilds/{guild}/channels", token, body)
                cid = created["id"]  # type: ignore[index]
                print(f"  channel created: #{ch['name']} → {cid}")
                rate_sleep()
            entry = {
                "id": cid,
                "type": ctype,
                "name": ch["name"],
                "agent": ch.get("agent"),
                "topic": ch.get("topic"),
            }
            channels_out[ch["key"]] = entry

    MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "guild_id": guild,
        "bot_id": me.get("id"),
        "roles": roles_out,
        "channels": channels_out,
        "provisioned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    MAP_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {MAP_FILE}")

    env_updates = {
        "DISCORD_GUILD_ID": guild,
        "DISCORD_ALERT_CHANNEL_ID": channels_out.get("boss_alerts", {}).get("id", ""),
        "DISCORD_DIGEST_CHANNEL_ID": channels_out.get("ops_digest", {}).get("id", ""),
        "DISCORD_BOSS_DESK_CHANNEL_ID": channels_out.get("boss_desk", {}).get("id", ""),
        "DISCORD_JARVIS_CHANNEL_ID": channels_out.get("jarvis", {}).get("id", ""),
        "DISCORD_ADMIN_CHANNEL_ID": channels_out.get("admin", {}).get("id", ""),
        "NOTIFY_CHANNELS": env.get("NOTIFY_CHANNELS") or "discord,telegram",
    }
    channel_env_map = {
        "closebot": "DISCORD_CLOSEBOT_CHANNEL_ID",
        "printful": "DISCORD_PRINTFUL_CHANNEL_ID",
        "shopify": "DISCORD_SHOPIFY_CHANNEL_ID",
        "seo_aeo_geo": "DISCORD_SEO_AEO_GEO_CHANNEL_ID",
        "meta_ads": "DISCORD_META_ADS_CHANNEL_ID",
        "acceptai": "DISCORD_ACCEPTAI_CHANNEL_ID",
        "calendar": "DISCORD_CALENDAR_CHANNEL_ID",
        "slack_avenou": "DISCORD_SLACK_AVENOU_CHANNEL_ID",
        "vocalitic": "DISCORD_VOCALITIC_CHANNEL_ID",
        "llm_lab": "DISCORD_LLM_LAB_CHANNEL_ID",
        "vapi": "DISCORD_VAPI_CHANNEL_ID",
        "sellthebizfast": "DISCORD_SELLTHEBIZFAST_CHANNEL_ID",
        "rocco": "DISCORD_ROCCO_CHANNEL_ID",
    }
    for key, env_key in channel_env_map.items():
        channel_id = channels_out.get(key, {}).get("id", "")
        if channel_id:
            env_updates[env_key] = channel_id
    env_updates = {k: v for k, v in env_updates.items() if v}
    upsert_env(env_updates)
    print("Updated .env channel IDs")
    print("\nNext:")
    print("  python3 /docker/clawsum/scripts/enable-discord.py")
    print("  python3 /docker/clawsum/scripts/apply-discord-bindings.py")
    print("  bash /docker/clawsum/scripts/discord-smoke-test.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
