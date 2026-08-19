#!/usr/bin/env python3
"""Scan the host Obsidian vault into paperclip-readable graph JSON."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
VAULT = Path(os.environ.get("CLAWSUM_OBSIDIAN", str(ROOT / "obsidian")))
DEST = Path(
    os.environ.get(
        "CLAWSUM_OBSIDIAN_GRAPH",
        str(ROOT / "paperclip-data" / ".hermes" / "obsidian-graph.json"),
    )
)

sys.path.insert(0, str(ROOT / "examples" / "hermes-cockpit" / "plugin" / "clawsum-cockpit" / "dashboard"))
from graphify_views import write_obsidian_snapshot  # noqa: E402

if not VAULT.is_dir():
    print(f"NO_VAULT {VAULT}")
    sys.exit(1)
payload = write_obsidian_snapshot(VAULT, DEST)
print(json.dumps({"dest": str(DEST), "nodes": len(payload.get("nodes") or []), "edges": len(payload.get("edges") or []), "scanned": payload.get("scanned")}, indent=2))
