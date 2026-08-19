#!/usr/bin/env bash
set -euo pipefail
F=/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py
docker exec clawsum-paperclip-1 bash -lc "
export PATH=/paperclip/.hermes-venv/bin:\$PATH
hermes dashboard --help 2>&1 | head -100
echo '==== origin check ===='
python3 - <<'PY'
from pathlib import Path
p=Path('/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py')
t=p.read_text()
# print function around origin_mismatch
i=t.find('origin_mismatch')
print(t[i-2500:i+1500])
print('==== ENV hints ====')
for needle in ['ALLOWED', 'TRUSTED', 'ORIGIN', 'allowed_hosts', 'HERMES_DASHBOARD']:
  if needle.lower() in t.lower():
    pass
import re
for m in re.finditer(r'HERMES_DASHBOARD_[A-Z0-9_]+|allowed_hosts|trusted_origins|ALLOW_ORIGIN', t):
  pass
print(sorted(set(re.findall(r'HERMES_DASHBOARD_[A-Z0-9_]+', t))))
print('allowed', sorted(set(re.findall(r'allowed_[a-z_]+', t, re.I)))[:30])
PY
"
