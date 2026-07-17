#!/usr/bin/env python3
"""
Configure OpenRouter as escalation path for non-OpenAI models.

Policy (locked):
- OpenAI / GPT models: Codex OAuth first, OPENAI_API_KEY fallback — never via OpenRouter
- Escalation / Claude / Gemini / etc.: openrouter/<author>/<model> fallbacks + /model catalog
- OpenAI models are NOT listed in OpenRouter fallbacks

Run after enforce-llm-codex-first.py when OPENROUTER_API_KEY is set:
  python3 /docker/clawsum/scripts/configure-openrouter-escalation.py
  cd /docker/clawsum && docker compose restart openclaw-gateway
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl
import llm_policy as policy

ROOT = Path("/docker/clawsum")
OPENCLAW = ROOT / "data/.openclaw"
CONFIG = OPENCLAW / "openclaw.json"
AGENTS = ghl.all_clawsum_openclaw_agent_ids()


def write_openrouter_auth_profiles(api_key: str) -> None:
    for agent_id in AGENTS:
        auth_path = OPENCLAW / "agents" / agent_id / "agent" / "auth-profiles.json"
        auth_path.parent.mkdir(parents=True, exist_ok=True)
        if auth_path.exists():
            data = json.loads(auth_path.read_text())
        else:
            data = {"version": 1, "profiles": {}}
        profiles = data.setdefault("profiles", {})
        profiles["openrouter:default"] = {
            "provider": "openrouter",
            "type": "api_key",
            "key": api_key,
        }
        auth_path.write_text(json.dumps(data, indent=2) + "\n")
        auth_path.chmod(0o600)
        print(f"  {agent_id}: openrouter:default written")


def patch_openclaw_config() -> None:
    cfg = json.loads(CONFIG.read_text())

    env_block = cfg.setdefault("env", {})
    env_block["OPENROUTER_API_KEY"] = policy.openrouter_api_key()

    plugins = cfg.setdefault("plugins", {})
    entries = plugins.setdefault("entries", {})
    entries["openrouter"] = {"enabled": True}
    allow = plugins.setdefault("allow", [])
    for name in ("openrouter", "openai", "codex", "microsoft"):
        if name not in allow:
            allow.append(name)

    order = cfg.setdefault("auth", {}).setdefault("order", {})
    order["openrouter"] = ["openrouter:default"]

    defaults = cfg.setdefault("agents", {}).setdefault("defaults", {})
    defaults["model"] = policy.primary_model_config()
    catalog = policy.model_catalog()
    if catalog:
        defaults.setdefault("models", {}).update(catalog)

    providers = cfg.setdefault("models", {}).setdefault("providers", {})
    providers.setdefault("openrouter", {}).setdefault("params", {}).setdefault(
        "provider",
        {
            "sort": "latency",
            "allow_fallbacks": True,
            "data_collection": "deny",
        },
    )

    # On-demand TTS/STT — auto off; agents use /tts or speech_api.py CLI
    messages = cfg.setdefault("messages", {})
    tts = messages.setdefault("tts", {})
    tts.setdefault("auto", "off")
    tts.setdefault("mode", "final")
    tts["provider"] = policy.speech_tts_provider()
    tts_providers = tts.setdefault("providers", {})
    tts_providers.setdefault("openai", {}).setdefault("model", policy.env_get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"))
    tts_providers["openai"].setdefault("speakerVoice", policy.env_get("OPENAI_TTS_VOICE", "alloy"))
    if policy.env_get("ELEVENLABS_API_KEY"):
        el = tts_providers.setdefault("elevenlabs", {})
        el.setdefault("modelId", policy.env_get("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2"))
        if policy.env_get("ELEVENLABS_VOICE_ID"):
            el.setdefault("speakerVoiceId", policy.env_get("ELEVENLABS_VOICE_ID"))

    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    model_cfg = defaults["model"]
    print(f"openclaw.json: model = {json.dumps(model_cfg)}")
    print(f"openclaw.json: openrouter catalog = {list(catalog.keys())}")


def main() -> None:
    print("=== OpenRouter escalation (non-OpenAI models only) ===\n")
    if not policy.openrouter_enabled():
        print("SKIP: OPENROUTER_API_KEY not set (or invalid sk-or- prefix)")
        print("Add key to .env and re-run. OpenAI/Codex path unchanged.")
        return

    if not CONFIG.exists():
        raise SystemExit(f"Missing {CONFIG}")

    api_key = policy.require_openrouter_key()
    patch_openclaw_config()
    print("\nAgent auth profiles:")
    write_openrouter_auth_profiles(api_key)

    print("\nEscalation models (OpenRouter only — no openai/*):")
    for ref in policy.escalation_models():
        print(f"  - {ref}")

    print("\nSpeech (on demand):")
    print(f"  STT provider: {policy.speech_stt_provider()}  CLI: python3 scripts/speech_api.py stt --help")
    print(f"  TTS provider: {policy.speech_tts_provider()}  CLI: python3 scripts/speech_api.py tts --help")
    print("\nRestart gateway:")
    print("  cd /docker/clawsum && docker compose restart openclaw-gateway")


if __name__ == "__main__":
    main()
