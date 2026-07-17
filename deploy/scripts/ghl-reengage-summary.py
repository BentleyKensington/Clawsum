#!/usr/bin/env python3
"""Print or refresh Telegram-friendly re-engage summary from latest audit artifacts.

Usage:
  python3 ghl-reengage-summary.py --slug ghl
  python3 ghl-reengage-summary.py --slug ghl --refresh  # rebuild LATEST from newest dated file
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl

ROOT = Path("/docker/clawsum")
OBS = ROOT / "obsidian"


def latest_dated_report(folder: Path) -> Path | None:
    reports = sorted(folder.glob("*-reengage-leads.md"), reverse=True)
    return reports[0] if reports else None


def rebuild_from_report(account: dict, report_path: Path) -> Path:
    """Parse dated markdown table/sections into LATEST (minimal — copy header stats)."""
    text = report_path.read_text(encoding="utf-8")
    today = report_path.name.split("-reengage")[0]
    base = OBS / "GHL" / account["obsidian_folder"] / "Recommendations"
    latest = base / "LATEST-REENGAGE-SUMMARY.md"
    viable_m = re.search(r"\*\*(\d+) viable leads\*\*", text)
    excluded_m = re.search(r"(\d+) excluded", text)
    viable = viable_m.group(1) if viable_m else "?"
    excluded = excluded_m.group(1) if excluded_m else "?"
    body = report_path.read_text(encoding="utf-8")
    # Pull full SMS section if present
    sms_section = ""
    if "## Full suggested SMS" in body:
        sms_section = body.split("## Full suggested SMS", 1)[1][:6000]

    lines = [
        f"# Re-engage summary — {account['display_name']}",
        "",
        f"**Updated:** {today} (refreshed from {report_path.name})",
        f"**Viable leads:** {viable} | **Excluded:** {excluded}",
        "",
        "Read this file when Boss asks for re-engage summary in Telegram.",
        "",
        f"Full report: `/home/node/obsidian/GHL/{account['obsidian_folder']}/Recommendations/{report_path.name}`",
        "",
    ]
    if sms_section:
        lines.append("## Lead details (from last audit)")
        lines.append(sms_section[:5500])
    latest.write_text("\n".join(lines), encoding="utf-8")
    text = latest.read_text(encoding="utf-8")
    ws = Path(f"/docker/clawsum/data/.openclaw/workspace-{account['id']}")
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "notes").mkdir(exist_ok=True)
    (ws / "notes" / "LATEST-REENGAGE-SUMMARY.md").write_text(text, encoding="utf-8")
    (ws / "REENGAGE.md").write_text(text, encoding="utf-8")
    (ws / "notes" / "REENGAGE.md").write_text(text, encoding="utf-8")
    return latest


def main() -> None:
    parser = argparse.ArgumentParser(description="Show MCO/GHL re-engage Telegram summary")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--refresh", action="store_true", help="Rebuild LATEST from newest dated report")
    args = parser.parse_args()

    account = ghl.account_by_slug(args.slug)
    if not account:
        raise SystemExit(f"Unknown slug: {args.slug}")

    folder = OBS / "GHL" / account["obsidian_folder"] / "Recommendations"
    latest = folder / "LATEST-REENGAGE-SUMMARY.md"

    if args.refresh or not latest.exists():
        report = latest_dated_report(folder)
        if not report:
            raise SystemExit(f"No re-engage reports in {folder}")
        latest = rebuild_from_report(account, report)
        print(f"Refreshed {latest}", file=sys.stderr)

    print(latest.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
