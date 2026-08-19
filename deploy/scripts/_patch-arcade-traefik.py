#!/usr/bin/env python3
from pathlib import Path

p = Path("/docker/traefik/dynamic/clawsum-com.yml")
t = p.read_text(encoding="utf-8")
router = """
    clawsum-arcade:
      rule: Host(`arcade.clawsum.com`)
      entryPoints:
        - websecure
      service: clawsum-arcade
      middlewares:
        - clawsum-ops-auth
        - clawsum-ops-user-header
      tls:
        certResolver: letsencrypt
"""
if "Host(`arcade.clawsum.com`)" not in t:
    marker = "    clawsum-grafana:\n      rule: Host(`grafana.clawsum.com`)"
    idx = t.find(marker)
    if idx < 0:
        raise SystemExit("grafana router not found")
    # insert arcade router after the grafana router block (before services)
    svc = t.find("\n  services:", idx)
    if svc < 0:
        raise SystemExit("services block not found")
    t = t[:svc] + "\n" + router + t[svc:]
    print("inserted arcade router before services")
else:
    print("router already present")
if "clawsum-arcade:" not in t.split("services:", 1)[-1]:
    t = t.rstrip() + """
    clawsum-arcade:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:2480
"""
    print("appended arcade service")
p.write_text(t if t.endswith("\n") else t + "\n", encoding="utf-8")
print("ok", p)
print("router", "Host(`arcade.clawsum.com`)" in p.read_text())
