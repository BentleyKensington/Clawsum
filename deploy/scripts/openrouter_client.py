#!/usr/bin/env python3
"""OpenRouter chat client for batch scripts — non-OpenAI models only."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

import llm_policy as policy

OPENROUTER_URL = policy.env_get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")


def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Call OpenRouter chat completions. Raises on HTTP errors."""
    api_key = policy.require_openrouter_key()
    slug = model or policy.env_get("OPENROUTER_ESCALATION_MODEL", "anthropic/claude-sonnet-4-6")
    api_model = policy.openrouter_api_model(slug)
    if api_model.startswith("openai/"):
        raise ValueError(
            "OpenRouter client is for non-OpenAI models only. Use OPENAI_API_KEY for GPT."
        )

    payload = {
        "model": api_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        f"{OPENROUTER_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": policy.env_get("OPENROUTER_HTTP_REFERER", "https://clawsum.local"),
            "X-Title": policy.env_get("OPENROUTER_APP_TITLE", "Clawsum"),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:800]
        raise RuntimeError(f"OpenRouter HTTP {e.code}: {body}") from e


def chat_text(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
) -> str:
    data = chat(messages, model=model, temperature=temperature)
    return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
