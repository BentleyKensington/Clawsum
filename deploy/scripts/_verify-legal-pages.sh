#!/usr/bin/env bash
set -eu
docker restart clawsum-marketing
sleep 2
PORT=$(docker port clawsum-marketing 8080 | head -1 | awk -F: '{print $NF}')
echo "port=$PORT"
curl -sS -o /dev/null -w "home:%{http_code}\n" "http://127.0.0.1:${PORT}/"
curl -sS -o /dev/null -w "privacy:%{http_code}\n" "http://127.0.0.1:${PORT}/privacy/"
curl -sS -o /dev/null -w "terms:%{http_code}\n" "http://127.0.0.1:${PORT}/terms/"
curl -sS -o /dev/null -w "privacy_noslash:%{http_code}\n" "http://127.0.0.1:${PORT}/privacy"
curl -sS "http://127.0.0.1:${PORT}/privacy/" | grep -o '<title>[^<]*</title>'
curl -sS "http://127.0.0.1:${PORT}/terms/" | grep -o '<title>[^<]*</title>'
