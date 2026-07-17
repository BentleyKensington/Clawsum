#!/usr/bin/env bash
set -eu
cd /docker/clawsum
mkdir -p data/prometheus data/grafana
chown -R 65534:65534 data/prometheus
chown -R 472:472 data/grafana
docker compose --profile monitoring up -d
sleep 5
curl -sS -o /dev/null -w "prometheus=%{http_code}\n" http://127.0.0.1:9090/-/healthy || true
curl -sS -o /dev/null -w "grafana=%{http_code}\n" http://127.0.0.1:3000/api/health || true
echo "Grafana: http://localhost:3000 (ssh -L 3000:127.0.0.1:3000 clawsum)"
