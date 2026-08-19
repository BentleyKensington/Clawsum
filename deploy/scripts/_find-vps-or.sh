#!/usr/bin/env bash
set -euo pipefail
# Inventory where OPENROUTER appears on Clawsum VPS (fingerprints only, no full keys).
python3 <<'PY'
from pathlib import Path
import hashlib, re, json, subprocess, os

pat = re.compile(r"sk-or-v1-[A-Za-z0-9_-]{10,}")
cur = ""
try:
    cur = json.loads(Path("/docker/clawsum/secrets/openrouter.json").read_text()).get("OPENROUTER_API_KEY","")
except Exception:
    pass
cur_fp = hashlib.sha256(cur.encode()).hexdigest()[:12] if cur else None
print("current_secrets_fp", cur_fp)

found = {}  # fp -> paths

def add(key, path, via=""):
    if not key or "sk-or" not in key:
        return
    key = key.strip().strip('"').strip("'")
    if not key.startswith("sk-or"):
        return
    fp = hashlib.sha256(key.encode()).hexdigest()[:12]
    rec = found.setdefault(fp, {"len": len(key), "prefix": key[:14], "paths": [], "same": key == cur})
    loc = f"{path}" + (f" ({via})" if via else "")
    if loc not in rec["paths"]:
        rec["paths"].append(loc)

# Broad text scan under /docker (bounded)
roots = [Path("/docker/clawsum"), Path("/docker/openclaw-qpr7"), Path("/docker/authelia"), Path("/docker/traefik")]
for root in roots:
    if not root.exists():
        print("missing_root", root)
        continue
    for f in root.rglob("*"):
        try:
            if not f.is_file() or f.stat().st_size > 8_000_000:
                continue
        except Exception:
            continue
        # skip huge venv/node trees unless name interesting
        parts = {p.lower() for p in f.parts}
        if "node_modules" in parts or ".hermes-venv" in parts or "site-packages" in parts:
            if "openrouter" not in f.name.lower() and f.suffix not in {".env", ".json"}:
                continue
        try:
            data = f.read_bytes()
        except Exception:
            continue
        if b"OPENROUTER" not in data and b"sk-or-v1-" not in data and b"openrouter" not in data.lower():
            continue
        # skip pure docs without keys if no sk-or
        if b"sk-or-v1-" not in data and b"OPENROUTER_API_KEY=" not in data:
            # still note mention-only files briefly
            if f.suffix in {".json", ".env", ".yml", ".yaml"} or "secret" in str(f).lower():
                print("MENTION_NO_KEY", f)
            continue
        text = data.decode("utf-8", "ignore")
        for m in pat.finditer(text):
            add(m.group(0), str(f))
        for line in text.splitlines():
            if "OPENROUTER_API_KEY" in line and "=" in line:
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                add(v, str(f), "envline")

# Docker container envs
try:
    names = subprocess.check_output(["docker", "ps", "-a", "--format", "{{.Names}}"], text=True).splitlines()
except Exception as e:
    names = []
    print("docker_err", e)
for name in names:
    try:
        out = subprocess.check_output(
            ["docker", "inspect", "-f", "{{range .Config.Env}}{{println .}}{{end}}", name],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        continue
    for line in out.splitlines():
        if "OPENROUTER" in line and "=" in line:
            k, _, v = line.partition("=")
            if "KEY" in k.upper() or v.startswith("sk-or"):
                add(v, f"docker:{name}", k)

# docker secrets / configs
try:
    secs = subprocess.check_output(["docker", "secret", "ls"], text=True, stderr=subprocess.DEVNULL)
    print("DOCKER_SECRETS")
    print(secs)
except Exception:
    print("no_docker_secrets_cmd")

print("\n=== DISTINCT OPENROUTER KEYS ===")
print("count", len(found))
for fp, rec in sorted(found.items(), key=lambda kv: (kv[1]["same"], kv[0])):
    tag = "CURRENT" if rec["same"] else "OTHER"
    print(f"[{tag}] fp={fp} len={rec['len']} prefix={rec['prefix']}...")
    for p in rec["paths"]:
        print("   ", p)

# List /docker/clawsum/secrets fully
print("\n=== /docker/clawsum/secrets ===")
sp = Path("/docker/clawsum/secrets")
if sp.exists():
    for c in sorted(sp.rglob("*")):
        print(c, c.stat().st_size if c.is_file() else "DIR")
else:
    print("MISSING")

# List possible secret dirs
print("\n=== secret-ish dirs ===")
for p in [
    Path("/docker/clawsum/secrets"),
    Path("/docker/clawsum/data/.openclaw-auth-secrets"),
    Path("/docker/clawsum/data/.openclaw/credentials"),
    Path("/docker/clawsum/data/.openclaw/agents"),
    Path("/docker/clawsum/paperclip-data/secrets"),
    Path("/run/secrets"),
]:
    print(p, "EXISTS" if p.exists() else "missing")
    if p.exists() and p.is_dir():
        for c in sorted(p.iterdir())[:40]:
            print(" ", c.name)
PY
