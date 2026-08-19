#!/usr/bin/env bash
set -euo pipefail
docker exec -u root clawsum-paperclip-1 bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
python3 - <<PY
from pathlib import Path
p = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/auth.py")
lines = p.read_text(errors="ignore").splitlines()
# find _codex_device_code_login definition
for i, line in enumerate(lines):
    if "def _codex_device_code_login" in line or "def login_openai_codex" in line or "def add_openai_codex" in line:
        print(f"FOUND {i+1}: {line}")
        for j in range(i, min(len(lines), i+120)):
            print(f"{j+1}:{lines[j]}")
        print("====")
# also search verification_uri prints in auth.py around device code poll
for i, line in enumerate(lines):
    if "_codex_device_code" in line or "verification_uri" in line or "user_code" in line:
        if i > 6900 and i < 7200:
            print(f"{i+1}:{line[:180]}")
PY
'
