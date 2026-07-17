#!/usr/bin/env python3
"""Shared LLM routing policy — Codex/OpenAI direct, OpenRouter for escalation only."""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path("/docker/clawsum")
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_CANDIDATES = [ROOT / ".env", REPO_ROOT.parent / ".env"]

PRIMARY_OPENAI_MODEL = "openai/gpt-5.4"
OPENROUTER_PREFIX = "openrouter/"


def _env_path() -> Path | None:
    for path in ENV_CANDIDATES:
        if path.exists():
            return path
    return None


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    path = _env_path()
    if path:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        out.setdefault(k, v)
    return out


def env_get(key: str, default: str = "") -> str:
    return load_env().get(key, default).strip() or default


def openrouter_api_key() -> str:
    return env_get("OPENROUTER_API_KEY")


def openrouter_enabled() -> bool:
    key = openrouter_api_key()
    return bool(key) and key.startswith("sk-or-")


def openrouter_model_ref(slug: str) -> str:
    slug = slug.strip()
    if not slug:
        return ""
    if slug.startswith(OPENROUTER_PREFIX):
        return slug
    return f"{OPENROUTER_PREFIX}{slug}"


def openrouter_api_model(slug: str) -> str:
    """Model id for OpenRouter HTTP API (no openrouter/ prefix)."""
    slug = slug.strip()
    if slug.startswith(OPENROUTER_PREFIX):
        return slug[len(OPENROUTER_PREFIX) :]
    return slug


def escalation_models() -> list[str]:
    """Non-OpenAI models routed via OpenRouter when primary GPT path fails or Boss escalates."""
    if not openrouter_enabled():
        return []
    models: list[str] = []
    for key in (
        "OPENROUTER_ESCALATION_MODEL",
        "OPENROUTER_CODING_MODEL",
        "OPENROUTER_RESEARCH_MODEL",
    ):
        slug = env_get(key)
        if slug:
            ref = openrouter_model_ref(slug)
            if ref not in models:
                models.append(ref)
    if not models:
        models.append(openrouter_model_ref("anthropic/claude-sonnet-4-6"))
    return models


def model_catalog() -> dict[str, dict]:
    """Allowlisted OpenRouter models for /model switching in OpenClaw."""
    catalog: dict[str, dict] = {}
    for ref in escalation_models():
        catalog[ref] = {"alias": ref.split("/")[-1]}
    return catalog


def primary_model_config() -> dict[str, object]:
    fallbacks = escalation_models()
    if fallbacks:
        return {"primary": PRIMARY_OPENAI_MODEL, "fallbacks": fallbacks}
    return {"primary": PRIMARY_OPENAI_MODEL}


def speech_stt_provider() -> str:
    return env_get("SPEECH_STT_PROVIDER", "openai").lower()


def speech_tts_provider() -> str:
    return env_get("SPEECH_TTS_PROVIDER", "openai").lower()


def require_openrouter_key() -> str:
    key = openrouter_api_key()
    if not key:
        raise SystemExit("OPENROUTER_API_KEY not set in .env")
    return key


# Lane → env key for OpenRouter slug (batch/cron scripts)
LANE_ENV_KEYS: dict[str, str] = {
    "default": "",  # use OpenAI batch model
    "cheap": "OPENROUTER_CHEAP_MODEL",
    "free": "OPENROUTER_FREE_MODEL",
    "frontier": "OPENROUTER_ESCALATION_MODEL",
    "coding": "OPENROUTER_CODING_MODEL",
    "research": "OPENROUTER_RESEARCH_MODEL",
    "glm": "OPENROUTER_CHEAP_MODEL",
}

LANE_DEFAULT_SLUGS: dict[str, str] = {
    "cheap": "z-ai/glm-4.5-air:free",
    "free": "openrouter/free",
    "frontier": "anthropic/claude-sonnet-4-6",
    "coding": "qwen/qwen3-coder",
    "research": "google/gemini-2.5-pro",
    "glm": "z-ai/glm-4.5-air:free",
}

BATCH_OPENAI_MODEL = "gpt-4o-mini"


def parse_llm_lane(text: str) -> str | None:
    """Extract llm:cheap|frontier|coding|glm|free|default from task text."""
    m = re.search(r"\bllm:(default|cheap|free|frontier|coding|research|glm)\b", text, re.I)
    return m.group(1).lower() if m else None


def resolve_batch_model(lane: str | None = None, task_text: str = "") -> tuple[str, str]:
    """
    Resolve (provider, model) for batch/cron scripts.
    provider: 'openai' | 'openrouter'
  model: API model slug
    """
    lane = lane or parse_llm_lane(task_text) or "default"
    if lane == "default":
        return "openai", env_get("GMAIL_TRIAGE_MODEL", BATCH_OPENAI_MODEL).replace("openai/", "")

    env_key = LANE_ENV_KEYS.get(lane, "OPENROUTER_ESCALATION_MODEL")
    slug = env_get(env_key, LANE_DEFAULT_SLUGS.get(lane, "anthropic/claude-sonnet-4-6"))
    return "openrouter", openrouter_api_model(slug)
