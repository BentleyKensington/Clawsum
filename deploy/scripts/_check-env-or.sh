#!/usr/bin/env bash
set -euo pipefail
ENV=/docker/clawsum/.env
echo "=== .env OPENROUTER / related lines (names + lens only) ==="
python3 <<'PY'
from pathlib import Path
p = Path("/docker/clawsum/.env")
print("path", p, "mtime", p.stat().st_mtime if p.exists() else None, "size", p.stat().st_size if p.exists() else None)
for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
    s = line.strip()
    if not s or s.startswith("#"):
        # still show commented OPENROUTER
        if "OPENROUTER" in line.upper() or "sk-or-v1-" in line:
            print(f"L{i}: COMMENTED_OR_HIDDEN len_line={len(line)}")
        continue
    if "OPENROUTER" in s.upper() or "sk-or-v1-" in s or s.startswith("OPENAI") or s.startswith("ANTHROPIC"):
        if "=" in s:
            k, _, v = s.partition("=")
            vv = v.strip().strip('"').strip("'")
            print(f"L{i}: {k.strip()} len={len(vv)} prefix={vv[:10]+'...' if vv else ''}")
        else:
            print(f"L{i}: {s[:40]}")
PY

echo "=== sibling backups ==="
ls -la --time-style=long-iso /docker/clawsum/.env* /docker/clawsum/*env* 2>/dev/null || true
find /docker/clawsum -maxdepth 2 -name '.env*' 2>/dev/null
find /root -maxdepth 2 -name '*clawsum*.env*' 2>/dev/null | sed -n '1,20p'

echo "=== containers still carrying OPENROUTER (fingerprint) ==="
python3 <<'PY'
import subprocess, hashlib
names = subprocess.check_output(["docker","ps","-a","--format","{{.Names}}"], text=True).splitlines()
for name in names:
    if "clawsum" not in name and "openclaw" not in name:
        continue
    out = subprocess.check_output(["docker","inspect","-f","{{range .Config.Env}}{{println .}}{{end}}", name], text=True)
    for line in out.splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            v = line.split("=",1)[1]
            print(name, "len", len(v), "fp", hashlib.sha256(v.encode()).hexdigest()[:12], "prefix", v[:10]+"...")
PY

echo "=== bash history lines mentioning OPENROUTER (no values) ==="
grep -n 'OPENROUTER\|\.env' /root/.bash_history 2>/dev/null | grep -i openrouter | sed -n '1,40p' || true

echo "=== /tmp leftover export from ceoroof copy? ==="
ls -la /tmp/*or* /tmp/*openrouter* /tmp/clawsum* 2>/dev/null | sed -n '1,40p' || true
