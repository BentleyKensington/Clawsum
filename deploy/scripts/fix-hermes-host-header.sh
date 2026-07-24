#!/bin/bash
set -euo pipefail
python3 <<'PY'
from pathlib import Path
p = Path("/docker/traefik/dynamic/clawsum-com.yml")
t = p.read_text()
if "hermes-host-rewrite" not in t:
    needle = """    clawsum-ops-user-header:
      headers:
        customRequestHeaders:
          X-Forwarded-User: \"boss\"
"""
    insert = needle + """    hermes-host-rewrite:
      headers:
        customRequestHeaders:
          Host: \"127.0.0.1:9119\"
"""
    if needle not in t:
        raise SystemExit("needle missing")
    t = t.replace(needle, insert, 1)
    old = """    clawsum-hermes:
      rule: Host(`hermes.clawsum.com`)
      entryPoints:
        - websecure
      service: clawsum-hermes
      middlewares:
        - clawsum-ops-auth
"""
    new = """    clawsum-hermes:
      rule: Host(`hermes.clawsum.com`)
      entryPoints:
        - websecure
      service: clawsum-hermes
      middlewares:
        - clawsum-ops-auth
        - hermes-host-rewrite
"""
    if old not in t:
        raise SystemExit("hermes router block missing")
    t = t.replace(old, new, 1)
    p.write_text(t)
    print("hermes rewrite added")
else:
    print("already present")
PY
docker restart traefik-traefik-1
sleep 4
PASS=$(cat /root/.clawsum-ops-pass)
code=$(curl -sS -o /tmp/h.out -w '%{http_code}' --resolve hermes.clawsum.com:443:127.0.0.1 -u "boss:${PASS}" https://hermes.clawsum.com/ -k || true)
echo "hermes=${code}"
head -c 180 /tmp/h.out; echo
# If still 400, try binding Hermes with --host 0.0.0.0 and trusted host env
if [[ "$code" == "400" ]]; then
  docker exec -u root clawsum-paperclip-1 bash -lc '
    pkill -f "hermes dashboard" 2>/dev/null || true
    H=/paperclip/.hermes-venv/bin/hermes
    [[ -x $H ]] || H=hermes
    # try help for host allow options
    $H dashboard --help 2>&1 | head -60 || true
    nohup env HERMES_DASHBOARD_ALLOWED_HOSTS="hermes.clawsum.com,127.0.0.1,localhost" \
      "$H" dashboard --host 0.0.0.0 --port 9119 --no-open >>/paperclip/logs/hermes-dashboard.log 2>&1 &
    sleep 3
    curl -sf -H "Host: hermes.clawsum.com" http://127.0.0.1:9119/ >/dev/null && echo local_host_ok || echo local_host_fail
    curl -sf http://127.0.0.1:9119/ >/dev/null && echo local_ip_ok || echo local_ip_fail
  '
  # point traefik at 127.0.0.1:9119 still; remove host rewrite if binding accepts hermes host
  sleep 1
  code=$(curl -sS -o /tmp/h.out -w '%{http_code}' --resolve hermes.clawsum.com:443:127.0.0.1 -u "boss:${PASS}" https://hermes.clawsum.com/ -k || true)
  echo "hermes_retry=${code}"
  head -c 180 /tmp/h.out; echo
fi
