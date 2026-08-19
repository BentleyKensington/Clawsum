#!/usr/bin/env bash
# Bind ArcadeDB Studio to https://arcade.clawsum.com behind Authelia.
# Does NOT run the full domain cutover (no Paperclip/OpenClaw restart).
set -euo pipefail
R=/docker/clawsum
T=/docker/traefik/dynamic/clawsum-com.yml
ENVF="$R/.env"

python3 - <<'PY'
from pathlib import Path
p = Path("/docker/traefik/dynamic/clawsum-com.yml")
t = p.read_text(encoding="utf-8")
if "clawsum-arcade:" in t and "Host(`arcade.clawsum.com`)" in t:
    print("traefik arcade router already present")
else:
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
    service = """    clawsum-arcade:
      loadBalancer:
        servers:
          - url: http://127.0.0.1:2480
"""
    if "clawsum-grafana:" in t and "clawsum-arcade:" not in t.split("services:", 1)[0]:
        t = t.replace(
            "        certResolver: letsencrypt\n\n  services:",
            "        certResolver: letsencrypt\n" + router + "\n  services:",
            1,
        )
    if "url: http://127.0.0.1:3000" in t and "127.0.0.1:2480" not in t:
        t = t.replace(
            "          - url: http://127.0.0.1:3000\n",
            "          - url: http://127.0.0.1:3000\n" + service,
            1,
        )
    p.write_text(t, encoding="utf-8")
    print("wrote arcade router+service into", p)
PY

set_kv() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENVF" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENVF"
  else
    echo "${key}=${val}" >>"$ENVF"
  fi
}
set_kv ARCADE_UI_HOST arcade.clawsum.com
set_kv CLAWSUM_ARCADE_URL https://arcade.clawsum.com

# runtime env for Hermes plugin
if [[ -f "$R/paperclip-data/.hermes/clawsum-runtime.env" ]]; then
  grep -q '^CLAWSUM_ARCADE_URL=' "$R/paperclip-data/.hermes/clawsum-runtime.env" \
    && sed -i 's|^CLAWSUM_ARCADE_URL=.*|CLAWSUM_ARCADE_URL=https://arcade.clawsum.com|' "$R/paperclip-data/.hermes/clawsum-runtime.env" \
    || echo 'CLAWSUM_ARCADE_URL=https://arcade.clawsum.com' >>"$R/paperclip-data/.hermes/clawsum-runtime.env"
  docker cp "$R/paperclip-data/.hermes/clawsum-runtime.env" \
    clawsum-paperclip-1:/paperclip/.hermes/clawsum-runtime.env 2>/dev/null || true
fi

# login launcher card
if [[ -f /tmp/login-index.html ]]; then
  mkdir -p "$R/sites/clawsum-com/login" "$R/data/sites/clawsum-com/login"
  cp -f /tmp/login-index.html "$R/sites/clawsum-com/login/index.html"
  cp -f /tmp/login-index.html "$R/data/sites/clawsum-com/login/index.html"
fi

# DNS if Porkbun keys exist
if grep -q '^PORKBUN_API_KEY=.\+' "$ENVF" 2>/dev/null; then
  set -a
  # shellcheck disable=SC1090
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" == *"="* ]] || continue
    key="${line%%=*}"
    val="${line#*=}"
    case "$key" in
      PORKBUN_API_KEY|PORKBUN_SECRET_KEY|CLAWSUM_VPS_IP|PORKBUN_DOMAIN) export "$key=$val" ;;
    esac
  done < "$ENVF"
  set +a
  python3 "$R/scripts/porkbun-sync-dns.py" || python3 /tmp/porkbun-sync-dns.py || echo DNS_SYNC_SKIP
else
  echo "NO_PORKBUN_KEYS — add A arcade.clawsum.com -> 76.13.97.82"
fi

echo "== smoke arcade host =="
sleep 2
curl -sS -o /dev/null -w "arcade:%{http_code}\n" --resolve arcade.clawsum.com:443:127.0.0.1 https://arcade.clawsum.com/ -k || true
echo ARCADE_PUBLIC_APPLIED
