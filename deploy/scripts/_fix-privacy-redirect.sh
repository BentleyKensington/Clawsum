#!/usr/bin/env bash
# Fix Google "privacy page non-responsive": /privacy was 301 → http://clawsum.com:8080/privacy/
set -euo pipefail
SRC=/docker/clawsum/deploy/sites/clawsum-com
DST=/docker/clawsum/data/sites/clawsum-com

echo "=== live nginx.conf (before) ==="
grep -nE 'privacy|absolute_redirect|port_in_redirect|return 301' "$DST/nginx.conf" || true

cp -a "$SRC/nginx.conf" "$DST/nginx.conf"
mkdir -p "$DST/privacy" "$DST/terms"
cp -a "$SRC/privacy/." "$DST/privacy/"
cp -a "$SRC/terms/." "$DST/terms/"

echo "=== live nginx.conf (after) ==="
grep -nE 'privacy|absolute_redirect|port_in_redirect|return 301' "$DST/nginx.conf"

docker exec clawsum-marketing nginx -t
docker exec clawsum-marketing nginx -s reload
sleep 1

echo "=== verify redirects (follow off) ==="
for u in \
  https://clawsum.com/privacy \
  https://clawsum.com/privacy/ \
  https://www.clawsum.com/privacy \
  https://clawsum.com/terms \
  https://clawsum.com/terms/
do
  curl -sS -o /dev/null -D - --max-time 8 "$u" | awk -v u="$u" '
    BEGIN{code=""; loc=""}
    /^HTTP/{code=$2}
    /^[Ll]ocation:/{loc=$0; sub(/^[Ll]ocation:[ \t]+/, "", loc); gsub(/\r/, "", loc)}
    END{printf "%s  %s  loc=%s\n", u, code, loc}
  '
done

echo "=== follow /privacy (no slash) must stay https and 200 ==="
curl -sS -o /tmp/priv.html -w "code=%{http_code} url=%{url_effective} ttfb=%{time_starttransfer}s total=%{time_total}s\n" \
  --max-time 10 -L https://clawsum.com/privacy
head -c 180 /tmp/priv.html; echo
grep -o '<title>[^<]*</title>' /tmp/priv.html || true
grep -c 'fonts.googleapis' /tmp/priv.html || echo "no google fonts (good)"
