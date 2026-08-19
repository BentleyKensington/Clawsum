#!/usr/bin/env python3
"""Replace user-facing Hermes branding with Clawsum (paths relative to repo root)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

JOBS = [
    (
        "deploy/sites/clawsum-com/index.html",
        [
            ("Hermes talks. Paperclip manages. OpenClaw acts.", "Clawsum talks. Paperclip manages. OpenClaw acts."),
            ("Hermes · Paperclip · OpenClaw", "Clawsum · Paperclip · OpenClaw"),
            ("Hermes conversation face", "Clawsum conversation face"),
            ("Hermes, Paperclip, OpenClaw", "Clawsum, Paperclip, OpenClaw"),
            ("01 · Hermes", "01 · Clawsum"),
            ("When Hermes sees", "When Clawsum sees"),
            ("question Hermes should", "question Clawsum should"),
            ("into Hermes memory", "into Clawsum memory"),
            ("Open Hermes.", "Open Clawsum."),
        ],
    ),
    (
        "deploy/sites/clawsum-com/offer/index.html",
        [
            ("Hermes talks, Paperclip manages, OpenClaw acts", "Clawsum talks, Paperclip manages, OpenClaw acts"),
            ("Hermes, Paperclip, OpenClaw", "Clawsum, Paperclip, OpenClaw"),
            ("what Hermes should ask", "what Clawsum should ask"),
            ("Hermes can summarize", "Clawsum can summarize"),
            ("You read it on Hermes", "You read it on Clawsum"),
            ("keeps Hermes from", "keeps Clawsum from"),
            ("Hermes UI face", "Clawsum UI face"),
            ("login / boss / hermes / grafana", "login / boss / clawsum chat / grafana"),
            ("Hermes · Paperclip · OpenClaw", "Clawsum · Paperclip · OpenClaw"),
        ],
    ),
    (
        "deploy/skills/CATALOG.md",
        [("| **Hermes** |", "| **Clawsum** |")],
    ),
    (
        "deploy/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/plugin_api.py",
        [
            ("for Hermes dashboard plugin", "for Clawsum dashboard plugin"),
            ("Review Hermes chat", "Review Clawsum chat"),
            ("for Hermes (questions", "for Clawsum (questions"),
            ("for Hermes / cockpit", "for Clawsum / cockpit"),
            ("Hermes memory", "Clawsum memory"),
            ('"hermes_instructions"', '"clawsum_instructions"'),
        ],
    ),
]


def main() -> None:
    for rel, pairs in JOBS:
        p = ROOT / rel
        t = p.read_text(encoding="utf-8")
        for a, b in pairs:
            n = t.count(a)
            t = t.replace(a, b)
            print(f"{rel}: {n}x {a[:48]!r}")
        p.write_text(t, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
