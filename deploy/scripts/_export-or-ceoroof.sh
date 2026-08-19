#!/usr/bin/env bash
# Export OpenRouter key + model slugs for Clawsum sync (no stdout of secrets).
set -euo pipefail
python3 <<'PY'
import json
from pathlib import Path
sec = Path("/docker/ceoroof/secrets/openrouter.json")
env = Path("/docker/ceoroof/.env")
key = ""
if sec.exists():
    data = json.loads(sec.read_text())
    key = (data.get("OPENROUTER_API_KEY") or data.get("api_key") or "").strip()
vals = {}
if env.exists():
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            vals[k.strip()] = v.strip().strip('"').strip("'")
if not key:
    key = vals.get("OPENROUTER_API_KEY", "")
if not key:
    raise SystemExit("no key")
out = Path("/tmp/clawsum-or-export.env")
lines = [
    f"OPENROUTER_API_KEY={key}",
    f"OPENROUTER_FREE_MODEL={vals.get('OPENROUTER_FREE_MODEL') or vals.get('OPENROUTER_S1_MODEL') or 'nvidia/nemotron-3-super-120b-a12b:free'}",
    f"OPENROUTER_S1_MODEL={vals.get('OPENROUTER_S1_MODEL') or vals.get('OPENROUTER_FREE_MODEL') or 'nvidia/nemotron-3-super-120b-a12b:free'}",
    f"OPENROUTER_ESCALATION_MODEL={vals.get('OPENROUTER_ESCALATION_MODEL') or 'anthropic/claude-sonnet-4.6'}",
]
out.write_text("\n".join(lines) + "\n")
out.chmod(0o600)
print("wrote", out, "bytes", out.stat().st_size)
PY
