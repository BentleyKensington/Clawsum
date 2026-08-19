#!/usr/bin/env bash
set -eu
cd /docker/clawsum
mkdir -p data/prometheus data/prometheus-textfile data/grafana grafana/provisioning/datasources grafana/provisioning/dashboards/json
chown -R 65534:65534 data/prometheus
chmod 0755 data/prometheus-textfile
chown -R 472:472 data/grafana grafana
chmod -R u+rwX,go+rX grafana
python3 scripts/clawsum-ops-metrics.py
cat >/etc/cron.d/clawsum-ops-metrics <<'EOF'
* * * * * root /usr/bin/python3 /docker/clawsum/scripts/clawsum-ops-metrics.py >>/var/log/clawsum-ops-metrics.log 2>&1
EOF
chmod 0644 /etc/cron.d/clawsum-ops-metrics
bash /docker/clawsum/scripts/install-chat-outage-replay.sh 2>/dev/null || true
docker compose --profile monitoring up -d
sleep 5
curl -sS -o /dev/null -w "prometheus=%{http_code}\n" http://127.0.0.1:9090/-/healthy || true
curl -sS -o /dev/null -w "grafana=%{http_code}\n" http://127.0.0.1:3000/api/health || true
echo "Grafana: https://grafana.clawsum.com (Authelia SSO)"
echo "Prometheus: ssh -L 9090:127.0.0.1:9090 clawsum → http://127.0.0.1:9090"
