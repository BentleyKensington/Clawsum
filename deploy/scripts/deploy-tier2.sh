#!/bin/bash
# Deploy Tier 2 on live VPS: MinIO, Redis, LangGraph image build, buckets, verify.
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
cd "$ROOT"

echo "=== Deploy Tier 2 ==="

# MinIO env defaults
if ! grep -q '^MINIO_ROOT_USER=' .env 2>/dev/null; then
  echo "MINIO_ROOT_USER=clawsum" >> .env
  echo "MINIO_ROOT_PASSWORD=$(openssl rand -hex 16)" >> .env
  echo "Added MinIO credentials to .env"
fi

mkdir -p data/minio data/backups langgraph/graphs

echo "==> Redis"
docker compose --profile orchestration up -d redis

echo "==> MinIO"
docker compose --profile storage up -d minio
sleep 5

echo "==> MinIO buckets"
bash scripts/init-minio-buckets.sh

echo "==> Build LangGraph image (OSS runner — no LangSmith license)"
docker build -t clawsum-langgraph:local langgraph/

echo "==> LangGraph API"
docker compose --profile orchestration up -d langgraph
sleep 10

echo "==> Verify Tier 2"
bash scripts/verify-tier2.sh
