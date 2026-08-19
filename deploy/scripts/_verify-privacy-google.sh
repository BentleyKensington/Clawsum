#!/usr/bin/env bash
# Verify legal pages the way Google's OAuth URL checker does.
set -euo pipefail

fail=0
check() {
  local label="$1" url="$2" expect_code="$3" expect_loc="${4:-}"
  local hdr body code loc ttfb
  hdr=$(mktemp)
  body=$(mktemp)
  ttfb=$(curl -sS -o "$body" -D "$hdr" -w "%{time_starttransfer}" --max-time 10 -A "Google-OAuth-Verification" "$url" || echo FAIL)
  code=$(awk 'BEGIN{c=""} /^HTTP/{c=$2} END{print c}' "$hdr")
  loc=$(awk 'BEGIN{IGNORECASE=1} /^Location:/{sub(/^Location:[ \t]+/,""); gsub(/\r/,""); print; exit}' "$hdr")
  printf "%-42s code=%-3s ttfb=%ss loc=%s\n" "$label" "$code" "$ttfb" "${loc:-}"
  if [ "$code" != "$expect_code" ]; then
    echo "  FAIL expected HTTP $expect_code"
    fail=1
  fi
  if [ -n "$expect_loc" ] && [ "$loc" != "$expect_loc" ]; then
    echo "  FAIL expected Location: $expect_loc"
    fail=1
  fi
  if echo "$loc" | grep -qE ':8080|http://'; then
    echo "  FAIL bad Location (internal/http)"
    fail=1
  fi
  if awk 'BEGIN{ok=1} /^HTTP/{if($2>=400)ok=0} END{exit ok?0:1}' "$hdr"; then
    :
  fi
  if echo "$ttfb" | grep -q FAIL; then
    echo "  FAIL curl timed out / failed"
    fail=1
  fi
  # Google crawler budget is tight; warn if >2s
  awk -v t="$ttfb" 'BEGIN{if(t+0>2){print "  WARN slow TTFB >2s"; exit 1}}' || true
  rm -f "$hdr" "$body"
}

echo "=== no-follow (crawler first hop) ==="
check "apex /privacy"              https://clawsum.com/privacy              301 "/privacy/"
check "apex /privacy/"             https://clawsum.com/privacy/             200
check "www /privacy"               https://www.clawsum.com/privacy          301 "/privacy/"
check "www /privacy/"              https://www.clawsum.com/privacy/         200
check "apex /terms"                https://clawsum.com/terms                301 "/terms/"
check "apex /terms/"               https://clawsum.com/terms/               200

echo
echo "=== follow redirects (must land https 200) ==="
for u in https://clawsum.com/privacy https://clawsum.com/privacy/ https://www.clawsum.com/privacy https://clawsum.com/terms; do
  out=$(curl -sS -o /tmp/vbody.html -w "final=%{url_effective} code=%{http_code} ttfb=%{time_starttransfer}s total=%{time_total}s" --max-time 10 -L -A "Google-OAuth-Verification" "$u")
  title=$(grep -o '<title>[^<]*</title>' /tmp/vbody.html | head -1)
  fonts=$(grep -c 'fonts.googleapis' /tmp/vbody.html || true)
  echo "$u"
  echo "  $out $title fonts.g=$fonts"
  echo "$out" | grep -q 'code=200' || { echo "  FAIL not 200"; fail=1; }
  echo "$out" | grep -q 'final=https://' || { echo "  FAIL left https"; fail=1; }
  echo "$out" | grep -q ':8080' && { echo "  FAIL landed on :8080"; fail=1; }
done

echo
echo "=== content sanity ==="
curl -sS --max-time 8 https://clawsum.com/privacy/ | grep -Eiq 'privacy policy|clawsum' || { echo "FAIL privacy body"; fail=1; }
curl -sS --max-time 8 https://clawsum.com/terms/   | grep -Eiq 'terms of service|clawsum' || { echo "FAIL terms body"; fail=1; }
echo "privacy + terms bodies look right"

echo
if [ "$fail" -eq 0 ]; then
  echo "VERIFY OK — paste https://clawsum.com/privacy/ into Google"
else
  echo "VERIFY FAILED"
  exit 1
fi
