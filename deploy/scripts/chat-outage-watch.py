#!/usr/bin/env python3
"""Watch Discord/Telegram/gateway health; on recovery, replay missed Discord messages.

Runs every minute via cron (install-chat-outage-replay.sh). Detects:
  - gateway container down
  - discord/telegram channel or plugin disabled in openclaw.json

On DOWN→UP (outage lasted >= MIN_OUTAGE_SECONDS), calls replay-missed-chat
for the outage window. Telegram reconnect is left to OpenClaw polling.

State: $CLAWSUM_ROOT/data/chat-replay/outage-state.json
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
STATE_DIR = ROOT / "data" / "chat-replay"
STATE_PATH = STATE_DIR / "outage-state.json"
GATEWAY = os.environ.get("OPENCLAW_GATEWAY_CONTAINER", "clawsum-openclaw-gateway-1")
MIN_OUTAGE_SECONDS = int(os.environ.get("CHAT_OUTAGE_MIN_SECONDS", "90"))
MAX_LOOKBACK_HOURS = int(os.environ.get("CHAT_OUTAGE_MAX_LOOKBACK_HOURS", "24"))
REPLAY_LIMIT = int(os.environ.get("REPLAY_LIMIT", "20"))
PRE_BUFFER_SECONDS = int(os.environ.get("CHAT_OUTAGE_PRE_BUFFER_SECONDS", "60"))
NOTIFY = os.environ.get("CHAT_OUTAGE_NOTIFY", "1") == "1"

# Ensure sibling import works when invoked as /docker/clawsum/scripts/...
sys.path.insert(0, str(Path(__file__).resolve().parent))


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def parse_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def load_state() -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.is_file():
        return {
            "healthy": None,
            "outage_started_at": None,
            "outage_reasons": [],
            "last_healthy_at": None,
            "last_replay_at": None,
            "last_replay_since": None,
            "last_replay_ok": 0,
            "last_replay_planned": 0,
            "events": [],
        }
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"healthy": None, "outage_started_at": None, "events": []}


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Cap event log
    events = state.get("events") or []
    state["events"] = events[-40:]
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


def gateway_running() -> bool:
    try:
        proc = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{.State.Running}}",
                GATEWAY,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return proc.returncode == 0 and proc.stdout.strip().lower() == "true"
    except (OSError, subprocess.SubprocessError):
        return False


def probe_channels() -> tuple[bool, list[str]]:
    """Return (healthy, reasons)."""
    reasons: list[str] = []
    if not gateway_running():
        reasons.append("gateway_down")

    cfg_path = ROOT / "data/.openclaw/openclaw.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        reasons.append(f"openclaw_json:{type(e).__name__}")
        return False, reasons

    channels = cfg.get("channels") or {}
    plugins = ((cfg.get("plugins") or {}).get("entries") or {})

    discord_ch = (channels.get("discord") or {}).get("enabled")
    telegram_ch = (channels.get("telegram") or {}).get("enabled")
    discord_pl = (plugins.get("discord") or {}).get("enabled")
    telegram_pl = (plugins.get("telegram") or {}).get("enabled")

    # Treat missing as unhealthy only when the key exists elsewhere as expected True;
    # Clawsum expects both on.
    if discord_ch is False:
        reasons.append("discord_channel_disabled")
    if discord_pl is False:
        reasons.append("discord_plugin_disabled")
    if telegram_ch is False:
        reasons.append("telegram_channel_disabled")
    if telegram_pl is False:
        reasons.append("telegram_plugin_disabled")

    # If keys are missing entirely, still flag — silent disable via delete shouldn't bypass watch
    if "discord" not in channels and "discord" not in plugins:
        reasons.append("discord_missing")
    if "telegram" not in channels and "telegram" not in plugins:
        reasons.append("telegram_missing")

    return len(reasons) == 0, reasons


def notify_recovery(outage_started: datetime, summary: dict, reasons: list[str]) -> None:
    if not NOTIFY:
        return
    try:
        from clawsum_notify import notify_boss  # type: ignore

        duration = int((now() - outage_started).total_seconds())
        text = (
            f"Chat channels recovered after ~{duration}s outage "
            f"({', '.join(reasons) or 'unknown'}).\n"
            f"Replay: planned={summary.get('planned', 0)} "
            f"ok={summary.get('delivered_ok', 0)} "
            f"fail={summary.get('delivered_fail', 0)} "
            f"since={summary.get('since')}"
        )
        notify_boss(text, severity="warning")
    except Exception as e:
        print(f"notify_skip {type(e).__name__}: {e}")


def append_event(state: dict, kind: str, **extra) -> None:
    ev = {"at": iso(now()), "kind": kind, **extra}
    state.setdefault("events", []).append(ev)


def run_once() -> int:
    state = load_state()
    healthy, reasons = probe_channels()
    prev = state.get("healthy")
    t = now()

    print(
        f"probe healthy={healthy} prev={prev} reasons={reasons} "
        f"outage_started={state.get('outage_started_at')}"
    )

    if not healthy:
        if state.get("outage_started_at") is None:
            state["outage_started_at"] = iso(t)
            append_event(state, "outage_start", reasons=reasons)
            print(f"OUTAGE_START {state['outage_started_at']} {reasons}")
        state["healthy"] = False
        state["outage_reasons"] = reasons
        save_state(state)
        return 0

    # healthy now
    outage_started = parse_iso(state.get("outage_started_at"))
    recovering = prev is False or (outage_started is not None)

    state["healthy"] = True
    state["last_healthy_at"] = iso(t)
    state["outage_reasons"] = []

    if not recovering:
        # Steady healthy — first boot with healthy=None just arms the watch
        if prev is None:
            append_event(state, "watch_armed")
            print("WATCH_ARMED")
        save_state(state)
        return 0

    # Recovery path
    if outage_started is None:
        outage_started = t - timedelta(seconds=MIN_OUTAGE_SECONDS)
    duration = (t - outage_started).total_seconds()
    start_reasons = []
    for ev in reversed(state.get("events") or []):
        if ev.get("kind") == "outage_start":
            start_reasons = ev.get("reasons") or []
            break

    append_event(
        state,
        "outage_end",
        duration_s=int(duration),
        reasons=start_reasons,
    )
    print(f"OUTAGE_END duration_s={int(duration)} reasons={start_reasons}")

    if duration < MIN_OUTAGE_SECONDS:
        print(f"SKIP_REPLAY short_outage {int(duration)}s < {MIN_OUTAGE_SECONDS}s")
        state["outage_started_at"] = None
        save_state(state)
        return 0

    since = outage_started - timedelta(seconds=PRE_BUFFER_SECONDS)
    earliest = t - timedelta(hours=MAX_LOOKBACK_HOURS)
    if since < earliest:
        since = earliest

    print(f"REPLAY_TRIGGER since={since.isoformat()}")
    import importlib.util

    replay_path = Path(__file__).resolve().parent / "replay-missed-chat.py"
    spec = importlib.util.spec_from_file_location("replay_missed_chat", replay_path)
    if spec is None or spec.loader is None:
        print("ERROR cannot load replay-missed-chat.py")
        state["outage_started_at"] = None
        save_state(state)
        return 1
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    dry = os.environ.get("DRY_RUN", "0") == "1"
    summary = mod.run_replay(
        since,
        dry_run=dry,
        limit=REPLAY_LIMIT,
        telegram_replay=False,
    )
    state["last_replay_at"] = iso(t)
    state["last_replay_since"] = summary.get("since")
    state["last_replay_ok"] = summary.get("delivered_ok", 0)
    state["last_replay_planned"] = summary.get("planned", 0)
    append_event(
        state,
        "replay",
        planned=summary.get("planned"),
        ok=summary.get("delivered_ok"),
        fail=summary.get("delivered_fail"),
        dry_run=dry,
    )
    state["outage_started_at"] = None
    save_state(state)

    notify_recovery(outage_started, summary, start_reasons)
    print(
        f"RECOVERY_DONE planned={summary.get('planned')} "
        f"ok={summary.get('delivered_ok')} fail={summary.get('delivered_fail')}"
    )
    return 0 if summary.get("delivered_fail", 0) == 0 else 1


def main() -> int:
    try:
        return run_once()
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
