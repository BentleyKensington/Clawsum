#!/usr/bin/env bash
set -euo pipefail
python3 <<'PY'
from pathlib import Path
import hashlib, re, json, os

current = ""
curp = Path("/docker/clawsum/secrets/openrouter.json")
if curp.exists():
    try:
        current = json.loads(curp.read_text()).get("OPENROUTER_API_KEY","") or ""
    except Exception:
        pass
print("current_fp", hashlib.sha256(current.encode()).hexdigest()[:12] if current else "none")

pat = re.compile(r"sk-or-v1-[A-Za-z0-9_-]{20,}")
found = {}  # fp -> {key, paths}

def add(key, path):
    if not key or not key.startswith("sk-or-v1-"):
        return
    fp = hashlib.sha256(key.encode()).hexdigest()[:12]
    rec = found.setdefault(fp, {"len": len(key), "prefix": key[:12], "suffix": key[-6:], "paths": set(), "same_as_current": key == current})
    rec["paths"].add(str(path))

roots = [
    Path("/docker/clawsum"),
    Path("/docker/openclaw-qpr7"),
    Path("/root"),
    Path("/var/backups"),
    Path("/opt"),
    Path("/tmp"),
]
# also old env names
extra_globs = [
    "/docker/clawsum/.env*",
    "/docker/clawsum/**/.env*",
    "/docker/clawsum/**/*secret*",
    "/docker/clawsum/**/*openrouter*",
    "/docker/clawsum/paperclip-data/**/*.json",
    "/docker/clawsum/data/**/*",
]

for root in roots:
    if not root.exists():
        print("skip_missing", root)
        continue
    for f in root.rglob("*"):
        try:
            if not f.is_file():
                continue
            if f.stat().st_size > 5_000_000:
                continue
        except Exception:
            continue
        # cheap filter
        name = f.name.lower()
        path_l = str(f).lower()
        interesting = (
            "openrouter" in name
            or "openrouter" in path_l
            or name.startswith(".env")
            or name.endswith(".env")
            or "secret" in name
            or name.endswith(".bak")
            or name.endswith(".old")
            or name.endswith(".backup")
            or "auth" in name
            or f.suffix in {".env", ".json", ".yml", ".yaml", ".txt", ".sh", ".py", ".md"}
        )
        if not interesting:
            continue
        try:
            data = f.read_bytes()
        except Exception:
            continue
        # skip binaries
        if b"\0" in data[:2048]:
            continue
        try:
            t = data.decode("utf-8", errors="ignore")
        except Exception:
            continue
        if "sk-or-v1-" not in t and "OPENROUTER_API_KEY" not in t:
            continue
        for m in pat.finditer(t):
            add(m.group(0), f)
        # also KEY=value forms that might be truncated oddly
        for line in t.splitlines():
            if "OPENROUTER_API_KEY" in line and "=" in line:
                v = line.split("=", 1)[1].strip().strip('"').strip("'").strip()
                if v.startswith("sk-or"):
                    add(v, f)

print("distinct_keys", len(found))
for fp, rec in sorted(found.items(), key=lambda kv: (-len(kv[1]["paths"]), kv[0])):
    print(f"KEY {fp} same_current={rec['same_as_current']} len={rec['len']} prefix={rec['prefix']}... suffix=...{rec['suffix']}")
    for p in sorted(rec["paths"])[:25]:
        print("  ", p)
    if len(rec["paths"]) > 25:
        print("   ...", len(rec["paths"])-25, "more")

# docker compose env files / inspect running containers for OPENROUTER
print("--- docker inspect env fingerprints ---")
import subprocess
try:
    names = subprocess.check_output(["docker","ps","--format","{{.Names}}"], text=True).splitlines()
except Exception as e:
    names = []
    print("docker_ps_err", e)
for name in names:
    try:
        out = subprocess.check_output(["docker","inspect","-f","{{range .Config.Env}}{{println .}}{{end}}", name], text=True)
    except Exception:
        continue
    for line in out.splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            v = line.split("=",1)[1]
            fp = hashlib.sha256(v.encode()).hexdigest()[:12]
            print(name, "OPENROUTER", fp, "len", len(v), "same", v==current)
PY

echo "=== git history in /docker/clawsum (if any) ==="
if [[ -d /docker/clawsum/.git ]]; then
  git -C /docker/clawsum log --all --oneline -- '*openrouter*' '*.env*' 2>/dev/null | sed -n '1,20p' || true
  git -C /docker/clawsum log -p --all -S 'sk-or-v1-' -- '*.env' '*openrouter*' 2>/dev/null | sed -n '1,5p' || true
else
  echo "no git in /docker/clawsum"
fi

echo "=== likely backup dirs ==="
ls -la /var/backups 2>/dev/null | sed -n '1,30p' || true
ls -la /docker/clawsum/*.bak /docker/clawsum/.env* 2>/dev/null || true
find /docker/clawsum -maxdepth 3 -name '*.bak' -o -name '.env.*' -o -name '*openrouter*' 2>/dev/null | sed -n '1,50p'
