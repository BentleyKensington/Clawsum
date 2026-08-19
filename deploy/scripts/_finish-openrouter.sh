#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
ENVF="$ROOT/.env"
SECDIR="$ROOT/secrets"
SEC="$SECDIR/openrouter.json"

echo "=== mirror OPENROUTER from .env → secrets ==="
python3 <<'PY'
import json
from pathlib import Path
env = Path("/docker/clawsum/.env")
key = ""
models = {}
for line in env.read_text().splitlines():
    if not line.strip() or line.strip().startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    k, v = k.strip(), v.strip().strip('"').strip("'")
    if k == "OPENROUTER_API_KEY":
        key = v
    if k in ("OPENROUTER_FREE_MODEL", "OPENROUTER_S1_MODEL", "OPENROUTER_ESCALATION_MODEL"):
        models[k] = v
if not key.startswith("sk-or-"):
    raise SystemExit(f"OPENROUTER_API_KEY missing/invalid in .env (len={len(key)})")
# ensure model defaults present in .env
need = {
    "OPENROUTER_FREE_MODEL": "nvidia/nemotron-3-super-120b-a12b:free",
    "OPENROUTER_S1_MODEL": "nvidia/nemotron-3-super-120b-a12b:free",
    "OPENROUTER_ESCALATION_MODEL": "anthropic/claude-sonnet-4.6",
}
lines = env.read_text().splitlines()
have = set()
out = []
for line in lines:
    if "=" in line and not line.strip().startswith("#"):
        k = line.split("=", 1)[0].strip()
        if k in need:
            have.add(k)
            # keep existing non-empty
            v = line.split("=", 1)[1].strip().strip('"').strip("'")
            if v:
                out.append(line)
                continue
            out.append(f"{k}={need[k]}")
            continue
    out.append(line)
for k, v in need.items():
    if k not in have:
        out.append(f"{k}={v}")
env.write_text("\n".join(out) + "\n")
env.chmod(0o600)
secdir = Path("/docker/clawsum/secrets")
secdir.mkdir(parents=True, exist_ok=True)
sec = Path("/docker/clawsum/secrets/openrouter.json")
sec.write_text(json.dumps({"OPENROUTER_API_KEY": key}, indent=2) + "\n")
sec.chmod(0o600)
print("secrets_ok len", len(key), "prefix", key[:10] + "...")
print("models", {k: models.get(k) or need[k] for k in need})
PY

echo "=== Hermes auth (Codex?) ==="
docker exec -u root -e HERMES_HOME=/paperclip/.hermes -e PATH=/paperclip/.hermes-venv/bin:/usr/bin:/bin \
  clawsum-paperclip-1 hermes auth list 2>&1 | sed -n '1,80p' || true

echo "=== OpenClaw openai-codex auth present? ==="
python3 <<'PY'
from pathlib import Path
roots = [
    Path("/docker/clawsum/data/.openclaw-auth-secrets"),
    Path("/docker/clawsum/data/.openclaw"),
]
for root in roots:
    print(root, "exists" if root.exists() else "missing")
    if not root.exists():
        continue
    hits = []
    for f in root.rglob("*"):
        if not f.is_file() or f.stat().st_size > 2_000_000:
            continue
        try:
            t = f.read_text(errors="ignore")
        except Exception:
            continue
        low = t.lower()
        if "openai-codex" in low or "chatgpt.com/backend-api/codex" in low or '"provider": "openai-codex"' in low:
            hits.append(str(f))
        elif "codex" in f.name.lower() and ("token" in low or "refresh" in low or "oauth" in low):
            hits.append(str(f))
    print("  codex-ish files", len(hits))
    for h in hits[:20]:
        print(" ", h)
PY

echo "=== configure Hermes openrouter routing ==="
cp -f /tmp/configure-hermes-openrouter.sh "$ROOT/scripts/configure-hermes-openrouter.sh" 2>/dev/null || true
if [[ ! -f "$ROOT/scripts/configure-hermes-openrouter.sh" ]]; then
  echo "missing configure script"
  exit 1
fi
sed -i 's/\r$//' "$ROOT/scripts/configure-hermes-openrouter.sh"
bash "$ROOT/scripts/configure-hermes-openrouter.sh"

echo "=== final model/fallback ==="
docker exec -u root clawsum-paperclip-1 python3 - <<'PY'
from pathlib import Path
t = Path("/paperclip/.hermes/config.yaml").read_text()
for line in t.splitlines():
    if line.startswith(("model", "fallback", "  ")) and (
        "provider" in line or "model" in line or "default" in line
        or line.startswith("model") or line.startswith("fallback")
    ):
        print(line)
PY
docker exec -u root -e HERMES_HOME=/paperclip/.hermes -e PATH=/paperclip/.hermes-venv/bin:/usr/bin:/bin \
  clawsum-paperclip-1 hermes fallback list 2>&1 | sed -n '1,40p' || true
echo DONE
