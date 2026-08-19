#!/usr/bin/env bash
set -euo pipefail
docker ps --filter name=arcade --format '{{.Names}} {{.Status}} {{.Ports}}'
grep ARCADEDB /docker/clawsum/.env | sed 's/PASSWORD=.*/PASSWORD=***/' || true
echo "=== try ready ==="
PASS=$(grep '^ARCADEDB_ROOT_PASSWORD=' /docker/clawsum/.env | cut -d= -f2- | tr -d '"' | tr -d "'")
curl -sS -m 5 -o /tmp/ar.out -w "http=%{http_code}\n" -u "root:${PASS}" http://127.0.0.1:2480/api/v1/ready || echo curl_fail
head -c 200 /tmp/ar.out; echo
echo "=== compose env for arcade ==="
docker inspect clawsum-arcadedb-1 --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -i arcade || true
echo "=== recent logs ==="
docker logs clawsum-arcadedb-1 --tail 30 2>&1 | tail -30
