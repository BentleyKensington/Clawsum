#!/usr/bin/env python3
"""
LLM Lab bake-off — compare models on a short Boss-prompt set.
Writes data/reports/llm-compare-latest.json. Paid runs notify; default is dry catalog.

  python3 llm-compare.py --dry-run
  python3 llm-compare.py --live   # uses OPENAI + OPENROUTER; notify Boss
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
OUT = ROOT / "data" / "reports" / "llm-compare-latest.json"

PROMPTS = [
    "One paragraph: should Clawsum adopt or side-by-side a new inbound tool that overlaps RevFactory?",
    "Draft a Boss-safe reply declining a vendor while asking one leading question.",
    "Extract three durable business facts from: 'Gerald wants morning briefs at 7:30 Chicago and Discord Boss Desk only.'",
]


def main() -> None:
    live = "--live" in sys.argv
    now = datetime.now(timezone.utc).isoformat()
    models = [
        {"id": "openai/gpt-5", "lane": "default", "note": "Daily GPT path"},
        {"id": os.environ.get("OPENROUTER_FRONTIER_MODEL", "openrouter/frontier"), "lane": "escalate", "note": "Codeword escalate / weak GPT"},
        {"id": "openai-codex", "lane": "coding", "note": "Coding lane"},
    ]
    payload = {
        "generated_at": now,
        "live": live,
        "status": "shell" if not live else "ran",
        "models": models,
        "prompts": PROMPTS,
        "scores": [],
        "recommendation": "Keep GPT for routine; escalate on thin answers or the word escalate. Re-run --live weekly.",
    }
    if live:
        payload["scores"].append(
            {
                "note": "Live scoring hook — wire openrouter_client.chat_json per model; do not silent-spend.",
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} live={live}")


if __name__ == "__main__":
    main()
