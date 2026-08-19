#!/bin/bash
set -euo pipefail
echo '==== established outbound 443 ===='
docker exec clawsum-openclaw-gateway-1 sh -lc '
  # parse /proc/net/tcp for ESTABLISHED (01) on port 443 (01BB)
  python3 - <<PY
import socket, struct
def parse(path, ipv6=False):
  rows=[]
  with open(path) as f:
    next(f)
    for line in f:
      parts=line.split()
      if parts[3] != "01":
        continue
      rem=parts[2]
      ip_hex, port_hex = rem.split(":")
      port=int(port_hex,16)
      if port != 443:
        continue
      if ipv6:
        # skip pretty print complexity
        rows.append(("v6", port))
      else:
        ip=socket.inet_ntoa(struct.pack("<L", int(ip_hex,16)))
        rows.append((ip, port))
  return rows
print("v4", parse("/proc/net/tcp"))
print("v6_count", len(parse("/proc/net/tcp6", True)))
PY
  echo --- ps ---
  ps aux | head -30
'
echo '==== recent full discord-related file log ===='
docker exec clawsum-openclaw-gateway-1 sh -lc 'grep -i discord /tmp/openclaw/openclaw-2026-08-04.log | tail -30'
echo '==== docker logs stderr? ===='
docker logs clawsum-openclaw-gateway-1 --since 5m 2>&1 | tail -30
