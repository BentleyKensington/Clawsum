#!/usr/bin/env bash
set +u
set -eo pipefail
echo "=== status api ==="
curl -sS http://127.0.0.1:9119/api/status | python3 -c 'import sys,json; d=json.load(sys.stdin); print({k:d.get(k) for k in sorted(d) if any(x in k.lower() for x in ("chat","agent","ws","gateway","status","auth","theme","error","model","connected","ready"))}); print("keys", sorted(d.keys())[:50])'

echo "=== cockpit health / archive / session-briefs ==="
for p in health archive session-briefs brief; do
  code=$(curl -sS -o /tmp/cp.json -w "%{http_code}" "http://127.0.0.1:9119/api/plugins/clawsum-cockpit/$p" || echo err)
  echo "$code $p"
  head -c 220 /tmp/cp.json; echo
done

echo "=== js syntax ==="
docker exec clawsum-paperclip-1 bash -lc 'command -v node; node --check /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js 2>&1 || python3 -c "
import pathlib
p=pathlib.Path(\"/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js\")
t=p.read_text()
print(\"bytes\", len(t))
print(\"has SidebarSlot\", \"SidebarSlot\" in t)
print(\"has registerSlot sidebar\", \"registerSlot(NAME, \\\"sidebar\\\"\" in t or \"registerSlot(NAME, \\\"sidebar\\\"\" in t)
print(\"has Session Startup Briefs\", \"Session Startup Briefs\" in t)
print(\"has clawsum-sidebar\", \"clawsum-sidebar\" in t)
"'

echo "=== css sidebar rules ==="
docker exec clawsum-paperclip-1 bash -lc 'grep -n "clawsum-sidebar\|sidebar" /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/style.css | head -40'

echo "=== manifest slots ==="
docker exec clawsum-paperclip-1 cat /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/manifest.json

echo "=== dashboard log tail ==="
docker exec clawsum-paperclip-1 bash -lc 'ls -lt /paperclip/.hermes/logs 2>/dev/null | head; tail -n 60 /paperclip/.hermes/logs/dashboard.log 2>/dev/null || tail -n 60 /paperclip/logs/hermes-dashboard.log 2>/dev/null || find /paperclip -name "*dashboard*.log" 2>/dev/null | head'

echo "=== boss via traefik ==="
curl -sk -o /tmp/boss.html -w "boss:%{http_code}\n" https://boss.clawsum.com/ || true
head -c 200 /tmp/boss.html; echo
curl -sk -o /tmp/boss-plugins.json -w "plugins:%{http_code}\n" https://boss.clawsum.com/api/dashboard/plugins || true
head -c 300 /tmp/boss-plugins.json; echo

echo "=== gateway / agent ==="
docker exec clawsum-paperclip-1 bash -lc 'ps aux | grep -E "[h]ermes|[g]ateway" | head -20; ss -lntp 2>/dev/null | head -30 || netstat -lntp 2>/dev/null | head -30'
