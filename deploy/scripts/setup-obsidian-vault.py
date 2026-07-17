#!/usr/bin/env python3
"""Setup Clawsum Obsidian vault on VPS (no CRLF issues)."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(SCRIPT_DIR))
import ghl_accounts as ghl

OBS = Path("/docker/clawsum/obsidian")
BASE = Path("/docker/clawsum/data/.openclaw")
REPORTS = Path("/docker/clawsum/data/reports")

CANON = [
    "Admin",
    "Coding",
    "Data",
    "RealEstate",
    "GHL",
    "Comms",
    "Research",
    "Planning",
    "Paperclip",
]

AGENTS = [
    ("admin", "Admin", "Ops liaison — reports, triage, cross-domain links"),
    ("coding", "Coding", "Code, CI, infra-as-code for Clawsum stack"),
    ("data", "Data", "ETL, scrapers, data pipelines, report builds"),
    ("realestate", "RealEstate", "Deals, comps, RE market (realestate DB only)"),
] + [
    (
        acc["id"],
        f"GHL/{acc['obsidian_folder']}",
        f"GHL {acc['display_name']} — CRM audits ({acc['schema_prefix']} schema only)",
    )
    for acc in ghl.accounts()
] + [
    ("comms", "Comms", "Messaging templates and comms drafts"),
    ("research", "Research", "Research briefs and synthesis"),
    ("planning", "Planning", "Roadmaps, priorities, ADRs"),
    ("paperclip", "Paperclip", "Orchestration and task breakdown notes"),
]


def merge_empty_drop(keep: str, drop: str) -> None:
    d = OBS / drop
    k = OBS / keep
    if not d.exists() or drop == keep:
        return
    if not any(d.iterdir()):
        d.rmdir()
        print(f"Removed empty duplicate: {drop}")


def chown_tree(p: Path) -> None:
    try:
        for root, dirs, files in os.walk(p):
            for name in dirs + files:
                os.chown(os.path.join(root, name), 1000, 1000)
        os.chown(p, 1000, 1000)
    except OSError:
        pass


def write_obsidian_md(agent: str, folder: str, scope: str) -> None:
    ws = BASE / f"workspace-{agent}"
    ws.mkdir(parents=True, exist_ok=True)
    text = f"""# OBSIDIAN.md — {agent}

## Vault path (container)

`/home/node/obsidian/{folder}/`

## Scope

{scope}

## Rules

- **Write here:** durable notes, briefs, ADRs, runbooks Boss should read in Obsidian.
- **Do not write:** secrets, API keys, raw credentials.
- **workspace notes/** = scratch/session; promote finished work into Obsidian.
- **Postgres** = structured truth; link IDs in notes, do not duplicate tables.
- Never write into another agent's Obsidian folder.

## Subfolders (create as needed)

- `Briefs/`, `Runbooks/`, `Decisions/`
- Admin also: `Reports/` (synced daily), `Inbox/` (Gmail triage summaries)
"""
    (ws / "OBSIDIAN.md").write_text(text, encoding="utf-8")
    boot = ws / "BOOT.md"
    if boot.exists() and "OBSIDIAN.md" not in boot.read_text(encoding="utf-8"):
        boot.write_text(
            boot.read_text(encoding="utf-8").replace(
                "DATABASE.md, today's", "DATABASE.md, OBSIDIAN.md, today's"
            ),
            encoding="utf-8",
        )


def main() -> None:
    OBS.mkdir(parents=True, exist_ok=True)
    (OBS / "_templates").mkdir(exist_ok=True)
    (OBS / "Admin" / "Reports").mkdir(parents=True, exist_ok=True)
    (OBS / "Admin" / "Inbox").mkdir(parents=True, exist_ok=True)

    merge_empty_drop("RealEstate", "Realestate")
    merge_empty_drop("GHL", "Ghl")
    for d in CANON + ["_templates"]:
        (OBS / d).mkdir(exist_ok=True)

    (OBS / "README.md").write_text(
        """# Clawsum Obsidian vault

Host path: `/docker/clawsum/obsidian`  
Container: `/home/node/obsidian`

See `/docker/clawsum/docs/OBSIDIAN-VAULT.md` for setup and desktop sync.
""",
        encoding="utf-8",
    )

    templates = {
        "daily-note.md": "# {{date}} — {{agent}}\n\n## Done\n\n## Next\n",
        "research-brief.md": "# Research brief — {{title}}\n\n## Question\n\n## Findings\n\n## Sources\n",
        "adr.md": "# ADR — {{title}}\n\n## Context\n\n## Decision\n\n## Consequences\n",
    }
    for name, body in templates.items():
        (OBS / "_templates" / name).write_text(body, encoding="utf-8")

    for agent, folder, scope in AGENTS:
        (OBS / folder / "README.md").write_text(
            f"# {folder}\n\nAgent: **{agent}**\n\n{scope}\n",
            encoding="utf-8",
        )
        write_obsidian_md(agent, folder, scope)

    count = 0
    for src in sorted(REPORTS.glob("global-*.md")):
        dest = OBS / "Admin" / "Reports" / src.name
        if not dest.exists() or src.stat().st_mtime > dest.stat().st_mtime:
            shutil.copy2(src, dest)
            count += 1
    latest = sorted(REPORTS.glob("global-*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if latest:
        link = OBS / "Admin" / "Latest-Report.md"
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(f"Reports/{latest[0].name}")

    chown_tree(OBS)
    for agent, _, _ in AGENTS:
        p = BASE / f"workspace-{agent}" / "OBSIDIAN.md"
        if p.exists():
            try:
                os.chown(p, 1000, 1000)
            except OSError:
                pass

    # cron
    cron_line = (
        "2 7 * * * TZ=America/Chicago "
        "/usr/bin/python3 /docker/clawsum/scripts/setup-obsidian-vault.py --sync-only "
        ">> /docker/clawsum/data/reports/obsidian-sync.log 2>&1"
    )
    try:
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        lines = [
            ln
            for ln in (existing.stdout or "").splitlines()
            if "obsidian" not in ln.lower() and "setup-obsidian-vault" not in ln
        ]
        lines.append(cron_line)
        subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True, check=True)
    except subprocess.CalledProcessError:
        pass

    print(f"Vault seeded. Reports synced: {count}")
    print(f"Files in vault: {sum(1 for _ in OBS.rglob('*.md'))}")


if __name__ == "__main__":
    import sys

    if "--sync-only" in sys.argv:
        REPORTS.mkdir(parents=True, exist_ok=True)
        count = 0
        for src in sorted(REPORTS.glob("global-*.md")):
            dest = OBS / "Admin" / "Reports" / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists() or src.stat().st_mtime > dest.stat().st_mtime:
                shutil.copy2(src, dest)
                count += 1
        latest = sorted(REPORTS.glob("global-*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if latest:
            link = OBS / "Admin" / "Latest-Report.md"
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(f"Reports/{latest[0].name}")
        chown_tree(OBS / "Admin")
        print(f"sync-only: {count} updated")
    else:
        main()
