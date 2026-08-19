#!/usr/bin/env python3
"""Append Jarvis/admin 'show your work' progress rules to SOUL files. No restarts."""
from __future__ import annotations

from pathlib import Path

MARKER = "## Show your work (live progress)"

BLOCK = """
## Show your work (live progress)

When Gerald is waiting on Discord, Telegram, or Boss chat, **narrate progress in short messages before the final answer**:

1. **Ack first** (one line): confirm you heard the ask.
2. **Then emit status lines** as you go, e.g.:
   - `Consulting agent: admin` / `coding` / `media` / `ghl-ave-rei` (Paperclip assignee)
   - `Checking Paperclip board…` / `Reading ops DB…` / `Calling GHL (readonly)…`
   - `Sourced via: <credential class>` — use **prefixes only** (`GHL_*`, `POSTGRES_*`, `MINIO_*`, Codex OAuth). **Never** print token values or raw keys.
3. **Final answer** after tools finish — concise, with what changed / what's next.

Rules:
- Prefer 2–5 progress lines max for a normal turn; do not spam.
- Never dump secrets, full env, or Authelia cookies.
- If you delegate via Paperclip, say the issue id when known (`CLA-…`).
- On Hermes/Boss UI, the early ack still applies; progress lines may follow in the same turn or as follow-ups when the channel supports multiple messages.
""".strip()


def patch(path: Path) -> str:
    if not path.is_file():
        return f"missing {path}"
    text = path.read_text(encoding="utf-8", errors="replace")
    if MARKER in text:
        return f"already {path}"
    # CRLF normalize lightly
    text = text.replace("\r\n", "\n")
    path.write_text(text.rstrip() + "\n\n" + BLOCK + "\n", encoding="utf-8")
    return f"patched {path}"


def main() -> int:
    roots = [
        Path("/docker/clawsum/data/.openclaw/workspace-admin/SOUL.md"),
        Path("/docker/clawsum/data/.openclaw/workspace-hermes/SOUL.md"),
        Path("/docker/clawsum/examples/hermes-cockpit/SOUL.md"),
        Path("/docker/clawsum/paperclip-data/.hermes/SOUL.md"),
    ]
    for p in roots:
        print(patch(p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
