#!/usr/bin/env python3
"""
Clawsum Boss notifier — Discord preferred, Telegram dual-write until verified.

Usage:
  from clawsum_notify import notify_boss, notify_digest
  notify_boss("🚨 alert text", severity="critical")
  notify_digest("📊 daily report…")

Env (see deploy/env.example):
  NOTIFY_CHANNELS=discord,telegram   # default dual-write
  DISCORD_BOT_TOKEN=
  DISCORD_ALERT_CHANNEL_ID=          # #boss-alerts
  DISCORD_DIGEST_CHANNEL_ID=         # #ops-digest
  TELEGRAM_BOT_TOKEN=
  TELEGRAM_ADMIN_CHAT_ID= / TELEGRAM_REPORT_CHAT_ID=
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
ENV_FILE = ROOT / ".env"


def load_env(path: Path | None = None) -> dict[str, str]:
    p = path or ENV_FILE
    out: dict[str, str] = {}
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, _, v = raw.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    # overlay process env
    for k, v in os.environ.items():
        if v and (k.startswith("DISCORD_") or k.startswith("TELEGRAM_") or k == "NOTIFY_CHANNELS"):
            out[k] = v
    return out


def channels_enabled(env: dict[str, str]) -> list[str]:
    raw = (env.get("NOTIFY_CHANNELS") or "discord,telegram").lower()
    return [c.strip() for c in raw.split(",") if c.strip()]


def _post_json(url: str, payload: dict, headers: dict[str, str], timeout: int = 30) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            **headers,
            "Content-Type": "application/json",
            "User-Agent": headers.get("User-Agent", "ClawsumHQ/1.0"),
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body) if body else {}


def send_discord(text: str, env: dict[str, str], channel_id: str) -> bool:
    token = (env.get("DISCORD_BOT_TOKEN") or "").strip()
    if not token or not channel_id:
        return False
    # Discord limit 2000 chars
    ok_any = False
    for i in range(0, len(text), 1900):
        chunk = text[i : i + 1900]
        try:
            _post_json(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                {"content": chunk},
                {
                    "Authorization": f"Bot {token}",
                    "User-Agent": "ClawsumHQ/1.0",
                },
            )
            ok_any = True
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            print(f"WARN: discord send failed ch={channel_id[-4:]}: HTTP {e.code} {detail}", flush=True)
            return False
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as e:
            print(f"WARN: discord send failed ch={channel_id[-4:]}: {e}", flush=True)
            return False
    return ok_any


def discord_digest_channels(env: dict[str, str]) -> list[str]:
    """Morning briefs / digests → Boss Desk only."""
    ch = (env.get("DISCORD_BOSS_DESK_CHANNEL_ID") or "").strip()
    if not ch:
        # Fallback if HQ map never provisioned boss_desk
        ch = (env.get("DISCORD_DIGEST_CHANNEL_ID") or "").strip()
    return [ch] if ch else []


def send_telegram(text: str, env: dict[str, str], chat_id: str) -> bool:
    token = (env.get("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token or not chat_id:
        return False
    for i in range(0, len(text), 3900):
        chunk = text[i : i + 3900]
        try:
            result = _post_json(
                f"https://api.telegram.org/bot{token}/sendMessage",
                {"chat_id": chat_id, "text": chunk},
                {},
            )
            if not result.get("ok"):
                raise RuntimeError(result)
        except (urllib.error.URLError, TimeoutError, RuntimeError) as e:
            print(f"WARN: telegram send failed: {e}", flush=True)
            return False
    return True


def telegram_admin_chat(env: dict[str, str]) -> str:
    return (
        env.get("TELEGRAM_ADMIN_CHAT_ID")
        or env.get("TELEGRAM_REPORT_CHAT_ID")
        or env.get("TELEGRAM_PAPERCLIP_GROUP_ID")
        or ""
    ).strip()


def telegram_report_chat(env: dict[str, str]) -> str:
    return (
        env.get("TELEGRAM_REPORT_CHAT_ID")
        or env.get("TELEGRAM_ADMIN_CHAT_ID")
        or ""
    ).strip()


def notify(
    text: str,
    *,
    kind: str = "alert",
    severity: str = "info",
    env: dict[str, str] | None = None,
    dry_run: bool = False,
) -> dict[str, bool]:
    """
    kind: alert → boss-alerts / admin chat
          digest → ops-digest / report chat
    """
    env = env or load_env()
    enabled = channels_enabled(env)
    results: dict[str, bool] = {}

    prefix = ""
    if severity == "critical":
        prefix = "🚨 "
    elif severity == "warn":
        prefix = "⚠️ "
    elif severity == "ok":
        prefix = "✅ "
    body = text if text.startswith(("🚨", "⚠️", "✅", "📊", "⏰")) else f"{prefix}{text}"

    if dry_run:
        print(f"--- notify dry-run kind={kind} channels={enabled} ---")
        print(body[:500])
        return {c: True for c in enabled}

    if "discord" in enabled:
        if kind == "alert":
            ch = (
                env.get("DISCORD_ALERT_CHANNEL_ID")
                or env.get("DISCORD_BOSS_DESK_CHANNEL_ID")
                or env.get("DISCORD_DIGEST_CHANNEL_ID")
                or ""
            ).strip()
            results["discord"] = send_discord(body, env, ch) if ch else False
        else:
            channels = discord_digest_channels(env)
            ok_any = False
            sent: list[str] = []
            for ch in channels:
                if send_discord(body, env, ch):
                    ok_any = True
                    sent.append(ch[-4:])
            results["discord"] = ok_any
            if sent:
                print(f"discord digest ok → …{', …'.join(sent)}", flush=True)
            elif not channels:
                print("WARN: no Discord digest/boss channel IDs configured", flush=True)

    if "telegram" in enabled:
        chat = telegram_admin_chat(env) if kind == "alert" else telegram_report_chat(env)
        results["telegram"] = send_telegram(body, env, chat)

    return results


def notify_boss(text: str, *, severity: str = "warn", **kw) -> dict[str, bool]:
    return notify(text, kind="alert", severity=severity, **kw)


def notify_digest(text: str, **kw) -> dict[str, bool]:
    return notify(text, kind="digest", severity="info", **kw)


def any_ok(results: dict[str, bool] | Iterable[bool]) -> bool:
    if isinstance(results, dict):
        return any(results.values())
    return any(results)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Clawsum dual-channel notify smoke")
    ap.add_argument("--digest", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("message", nargs="?", default="Clawsum notify smoke test")
    args = ap.parse_args()
    if args.digest:
        r = notify_digest(args.message, dry_run=args.dry_run)
    else:
        r = notify_boss(args.message, severity="ok", dry_run=args.dry_run)
    print(r)
    raise SystemExit(0 if any_ok(r) or args.dry_run else 1)
