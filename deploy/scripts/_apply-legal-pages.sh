#!/usr/bin/env bash
set -euo pipefail
R=/docker/clawsum
SRC=/tmp/clawsum-legal
for DST in "$R/sites/clawsum-com" "$R/data/sites/clawsum-com" "$R/deploy/sites/clawsum-com"; do
  if [[ -d "$DST" ]] || [[ "$DST" == "$R/data/sites/clawsum-com" ]]; then
    mkdir -p "$DST/privacy" "$DST/terms"
    cp -f "$SRC/privacy/index.html" "$DST/privacy/index.html"
    cp -f "$SRC/terms/index.html" "$DST/terms/index.html"
    cp -f "$SRC/styles.css" "$DST/styles.css"
    cp -f "$SRC/sitemap.xml" "$DST/sitemap.xml"
    cp -f "$SRC/nginx.conf" "$DST/nginx.conf"
    cp -f "$SRC/index.html" "$DST/index.html"
    cp -f "$SRC/offer/index.html" "$DST/offer/index.html"
    echo "synced $DST"
  fi
done
docker restart clawsum-marketing
sleep 2
curl -sS -o /dev/null -w "privacy:%{http_code} %{redirect_url}\n" http://127.0.0.1:8088/privacy/ || \
curl -sS -o /dev/null -w "privacy8080:%{http_code}\n" http://127.0.0.1:8080/privacy/ || true
# discover marketing port
PORT=$(docker inspect -f '{{(index (index .NetworkSettings.Ports "8080/tcp") 0).HostPort}}' clawsum-marketing 2>/dev/null || echo 8088)
echo "marketing_port=$PORT"
curl -sS -o /dev/null -w "home:%{http_code}\n" "http://127.0.0.1:${PORT}/"
curl -sS -o /dev/null -w "privacy:%{http_code}\n" "http://127.0.0.1:${PORT}/privacy/"
curl -sS -o /dev/null -w "terms:%{http_code}\n" "http://127.0.0.1:${PORT}/terms/"
curl -sS -o /dev/null -w "privacy_redirect:%{http_code}\n" "http://127.0.0.1:${PORT}/privacy"
curl -sS "http://127.0.0.1:${PORT}/privacy/" | grep -o '<title>[^<]*</title>'
curl -sS "http://127.0.0.1:${PORT}/terms/" | grep -o '<title>[^<]*</title>'
