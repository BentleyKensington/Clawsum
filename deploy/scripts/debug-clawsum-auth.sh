#!/bin/bash
set -euo pipefail
PASS=$(cat /root/.clawsum-ops-pass)
# Extract hash from yml and verify
python3 - <<'PY'
from pathlib import Path
import re, subprocess, tempfile, os
t=Path('/docker/traefik/dynamic/clawsum-com.yml').read_text()
m=re.search(r'- "(boss:\$\$2y\$\$[^"]+)"', t)
assert m, 'hash not found'
raw=m.group(1).replace('$$','$')
print('raw_hash', raw)
open('/tmp/htcheck','w').write(raw+'\n')
passw=open('/root/.clawsum-ops-pass').read().strip()
r=subprocess.run(['htpasswd','-vb','/tmp/htcheck','boss',passw], capture_output=True, text=True)
print('htpasswd_verify', r.returncode, r.stderr.strip() or r.stdout.strip())
PY
echo '--- curl verbose ---'
curl -sv --resolve hermes.clawsum.com:443:127.0.0.1 -u "boss:${PASS}" https://hermes.clawsum.com/ -k -o /tmp/out.html 2>/tmp/curl.err
head -40 /tmp/curl.err
echo 'body_head:'; head -5 /tmp/out.html
echo '--- traefik routers ---'
docker exec traefik-traefik-1 wget -qO- http://127.0.0.1:8080/api/http/routers 2>/dev/null | head -c 200 || true
# Try usersFile approach
htpasswd -nbB boss "$PASS" | tr -d '\r' > /docker/traefik/dynamic/clawsum-ops.htpasswd
chmod 644 /docker/traefik/dynamic/clawsum-ops.htpasswd
python3 - <<'PY'
from pathlib import Path
p=Path('/docker/traefik/dynamic/clawsum-com.yml')
t=p.read_text()
old='''    clawsum-ops-auth:
      basicAuth:
        users:
          - "boss:$$2y$$05$$'''
# replace entire basicAuth block
import re
t2=re.sub(
    r'clawsum-ops-auth:\n\s+basicAuth:\n\s+users:\n\s+- "[^"]+"',
    'clawsum-ops-auth:\n      basicAuth:\n        usersFile: /dynamic/clawsum-ops.htpasswd',
    t,
    count=1,
)
p.write_text(t2)
print('switched to usersFile')
print(p.read_text().split('clawsum-ops-auth:')[1][:200])
PY
docker restart traefik-traefik-1
sleep 4
curl -sS -o /dev/null -w 'hermes_after=%{http_code}\n' --resolve hermes.clawsum.com:443:127.0.0.1 -u "boss:${PASS}" https://hermes.clawsum.com/ -k
curl -sS -o /dev/null -w 'boss_after=%{http_code}\n' --resolve boss.clawsum.com:443:127.0.0.1 -u "boss:${PASS}" https://boss.clawsum.com/api/health -k
