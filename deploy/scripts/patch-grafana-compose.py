#!/usr/bin/env python3
"""Patch clawsum docker-compose grafana service for Authelia + provisioning."""
from pathlib import Path

p = Path("/docker/clawsum/docker-compose.yml")
text = p.read_text()
if "GF_AUTH_BASIC_ENABLED" in text and "GF_SERVER_ROOT_URL" in text:
    print("compose already patched")
    raise SystemExit(0)

needle = '      # Traefik basic auth is the only human gate — auto-login via X-Forwarded-User\n'
if needle not in text:
    needle = '      # Traefik basic auth is the only human gate - auto-login via X-Forwarded-User\n'

insert = """      # Authelia (Traefik forwardAuth) is the human gate — auto-login via X-Forwarded-User
      GF_SERVER_ROOT_URL: ${CLAWSUM_GRAFANA_URL:-https://grafana.clawsum.com}
      GF_SERVER_DOMAIN: grafana.clawsum.com
      GF_AUTH_BASIC_ENABLED: \"false\"
      GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH: /etc/grafana/provisioning/dashboards/json/clawsum-health.json
"""

if needle in text:
    text = text.replace(needle, insert, 1)
elif "GF_AUTH_DISABLE_LOGIN_FORM: \"true\"" in text and "GF_AUTH_BASIC_ENABLED" not in text:
    text = text.replace(
        '      GF_AUTH_DISABLE_LOGIN_FORM: "true"\n',
        '      GF_AUTH_DISABLE_LOGIN_FORM: "true"\n'
        '      GF_SERVER_ROOT_URL: ${CLAWSUM_GRAFANA_URL:-https://grafana.clawsum.com}\n'
        '      GF_SERVER_DOMAIN: grafana.clawsum.com\n'
        '      GF_AUTH_BASIC_ENABLED: "false"\n'
        '      GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH: /etc/grafana/provisioning/dashboards/json/clawsum-health.json\n',
        1,
    )
else:
    raise SystemExit("Could not find grafana env block to patch")

# Ensure user 472
if "\n  grafana:\n" in text and 'user: "472:472"' not in text:
    text = text.replace(
        "\n  grafana:\n    image: grafana/grafana:11.4.0\n",
        '\n  grafana:\n    image: grafana/grafana:11.4.0\n    user: "472:472"\n',
        1,
    )

p.write_text(text)
print("patched", p)
