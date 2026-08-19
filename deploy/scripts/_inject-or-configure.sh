#!/usr/bin/env bash
# Inject exported OpenRouter env into Clawsum host .env + secrets, then configure Hermes.
set -euo pipefail
EXPORT="${1:-/tmp/clawsum-or-export.env}"
ROOT=/docker/clawsum
ENVF="$ROOT/.env"
SECDIR="$ROOT/secrets"
SEC="$SECDIR/openrouter.json"

if [[ ! -f "$EXPORT" ]]; then
  echo "missing export $EXPORT"
  exit 1
fi

python3 <<PY
import json
from pathlib import Path
export = Path("$EXPORT")
vals = {}
for line in export.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("=")
        vals[k.strip()] = v.strip()
key = vals.get("OPENROUTER_API_KEY", "")
if not key:
    raise SystemExit("no OPENROUTER_API_KEY in export")
envp = Path("$ENVF")
lines = envp.read_text().splitlines() if envp.exists() else []
keep = []
drop = {
    "OPENROUTER_API_KEY",
    "OPENROUTER_FREE_MODEL",
    "OPENROUTER_S1_MODEL",
    "OPENROUTER_ESCALATION_MODEL",
}
for line in lines:
    if "=" in line and not line.strip().startswith("#"):
        k = line.split("=", 1)[0].strip()
        if k in drop:
            continue
    keep.append(line)
# ensure trailing newline hygiene
while keep and keep[-1] == "":
    keep.pop()
keep.append("")
keep.append(f"OPENROUTER_API_KEY={key}")
keep.append(f"OPENROUTER_FREE_MODEL={vals.get('OPENROUTER_FREE_MODEL', 'nvidia/nemotron-3-super-120b-a12b:free')}")
keep.append(f"OPENROUTER_S1_MODEL={vals.get('OPENROUTER_S1_MODEL', 'nvidia/nemotron-3-super-120b-a12b:free')}")
keep.append(f"OPENROUTER_ESCALATION_MODEL={vals.get('OPENROUTER_ESCALATION_MODEL', 'anthropic/claude-sonnet-4.6')}")
envp.write_text("\n".join(keep) + "\n")
envp.chmod(0o600)
secdir = Path("$SECDIR")
secdir.mkdir(parents=True, exist_ok=True)
sec = Path("$SEC")
sec.write_text(json.dumps({"OPENROUTER_API_KEY": key}, indent=2) + "\n")
sec.chmod(0o600)
print("injected OpenRouter into", envp, "and", sec)
print("free", vals.get("OPENROUTER_FREE_MODEL"))
print("escalation", vals.get("OPENROUTER_ESCALATION_MODEL"))
PY

rm -f "$EXPORT"
cp -f /tmp/configure-hermes-openrouter.sh "$ROOT/scripts/configure-hermes-openrouter.sh"
sed -i 's/\r$//' "$ROOT/scripts/configure-hermes-openrouter.sh"
bash "$ROOT/scripts/configure-hermes-openrouter.sh"
