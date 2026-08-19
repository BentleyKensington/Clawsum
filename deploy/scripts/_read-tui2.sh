#!/usr/bin/env bash
set -euo pipefail
docker exec clawsum-paperclip-1 bash -lc 'python3 -c "
from pathlib import Path
main = Path(\"/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/main.py\").read_text()
print(\"len\", len(main))
i = main.find(\"def _make_tui_argv\")
print(\"make_idx\", i)
print(main[i:i+2200] if i>=0 else \"NO\")
"'
