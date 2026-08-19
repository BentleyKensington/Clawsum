#!/usr/bin/env bash
set -eu
echo "=== DNS ==="
getent ahostsv4 clawsum.com | head -5
getent ahostsv6 clawsum.com | head -5 || echo "no_aaaa"
echo "=== public https timings ==="
for u in https://clawsum.com/privacy/ https://clawsum.com/privacy https://www.clawsum.com/privacy/ https://clawsum.com/terms/; do
  curl -sS -o /tmp/p.body -w "$u code=%{http_code} redir=%{redirect_url} ttfb=%{time_starttransfer}s total=%{time_total}s size=%{size_download}\n" --max-time 15 "$u" || echo "$u FAIL"
done
echo "=== title ==="
grep -o '<title>[^<]*</title>' /tmp/p.body || true
echo "=== traefik marketing rule ==="
grep -nE 'clawsum-marketing|Host\(`clawsum.com`\)|privacy' /docker/traefik/dynamic/clawsum-com.yml | head -30
echo "=== marketing up ==="
docker inspect -f '{{.State.Status}} {{.State.StartedAt}}' clawsum-marketing
