#!/bin/bash
set -euo pipefail
PASS=$(cat /root/.clawsum-ops-pass)
echo "pass_ok len=${#PASS}"
curl -sv --resolve hermes.clawsum.com:443:127.0.0.1 -u "boss:${PASS}" https://hermes.clawsum.com/ -k -o /tmp/h.out 2>/tmp/h.err || true
echo '--- headers ---'
grep -E 'HTTP/|WWW-Authenticate|^< ' /tmp/h.err | head -25
echo '--- body ---'
head -30 /tmp/h.out || true
echo '--- codes ---'
for item in \
  "clawsum.com:/:public" \
  "www.clawsum.com:/:public" \
  "hermes.clawsum.com:/:auth" \
  "boss.clawsum.com:/api/health:auth" \
  "login.clawsum.com:/:auth" \
  "grafana.clawsum.com:/:auth" \
  "openclaw.clawsum.com:/:auth" \
  "connect.clawsum.com:/:auth"; do
  IFS=':' read -r host path mode <<<"${item}"
  # fix path parsing for host with port-like - use different delimiter
  :
done

check() {
  local host=$1 path=$2 mode=$3
  if [[ $mode == public ]]; then
    code=$(curl -sS -o /dev/null -w '%{http_code}' --resolve "${host}:443:127.0.0.1" "https://${host}${path}" -k || true)
  else
    code=$(curl -sS -o /dev/null -w '%{http_code}' --resolve "${host}:443:127.0.0.1" -u "boss:${PASS}" "https://${host}${path}" -k || true)
  fi
  echo "${host}${path}=${code}"
}
check clawsum.com / public
check www.clawsum.com / public
check hermes.clawsum.com / auth
check boss.clawsum.com /api/health auth
check login.clawsum.com / auth
check grafana.clawsum.com / auth
check openclaw.clawsum.com / auth
check connect.clawsum.com / auth
