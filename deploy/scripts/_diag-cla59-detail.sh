#!/usr/bin/env bash
set -euo pipefail
echo "=== who owns 3100/3101 ==="
for pid in $(ss -lntp | sed -n 's/.*:\(3100\|3101\).*pid=\([0-9]*\).*/\2/p' | sort -u); do
  echo "pid=$pid"
  ps -fp "$pid" || true
  tr '\0' ' ' < /proc/$pid/cmdline; echo
  ls -la /proc/$pid/cwd 2>/dev/null || true
done

echo "=== paperclip container ==="
docker port clawsum-paperclip-1 2>/dev/null || true
docker inspect clawsum-paperclip-1 --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} ip={{$v.IPAddress}}{{"\n"}}{{end}}'
docker inspect clawsum-paperclip-1 --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -Ei 'PORT|HOST|URL|PAPERCLIP|AUTH|LISTEN' | sed -E 's/(SECRET|TOKEN|KEY|PASSWORD)=.*/\1=SET/' || true

echo "=== gateway container reachability ==="
docker exec clawsum-openclaw-gateway-1 sh -c '
getent hosts paperclip clawsum-paperclip-1 host.docker.internal 172.17.0.1 2>/dev/null || true
for u in \
  http://127.0.0.1:3100/api/health \
  http://127.0.0.1:3101/api/health \
  http://host.docker.internal:3100/api/health \
  http://host.docker.internal:3101/api/health \
  http://172.17.0.1:3100/api/health \
  http://172.17.0.1:3101/api/health \
  http://clawsum-paperclip-1:3100/api/health \
  http://paperclip:3100/api/health
 do
  code=$(curl -sS -m 2 -o /dev/null -w "%{http_code}" "$u" 2>/dev/null || echo fail)
  echo "$u => $code"
 done
'

echo "=== CLA-59 detail + 3101 ==="
python3 /tmp/_cla59_detail.py

echo "=== CLA-59 artifacts ==="
ls -la /docker/clawsum/data/.openclaw/workspace-ghl-ave-rei/notes/activity-archive/CLA-59* 2>/dev/null || true
echo "--- disposition ---"
sed -n '1,100p' /docker/clawsum/data/.openclaw/workspace-ghl-ave-rei/notes/activity-archive/CLA-59-final-disposition.md
echo "--- closeout.json ---"
cat /docker/clawsum/data/.openclaw/workspace-ghl-ave-rei/notes/activity-archive/CLA-59-closeout.json
echo "--- TOOLS/AGENTS paperclip refs ---"
grep -n -E 'paperclip|3100|3101|/api' /docker/clawsum/data/.openclaw/workspace-ghl-ave-rei/TOOLS.md 2>/dev/null | head -50 || true
grep -n -E 'paperclip|3100|3101|/api' /docker/clawsum/data/.openclaw/workspace-ghl-ave-rei/AGENTS.md 2>/dev/null | head -50 || true
grep -n -E 'paperclip|3100|3101|/api' /docker/clawsum/data/.openclaw/workspace-ghl-ave-rei/SOUL.md 2>/dev/null | head -50 || true
