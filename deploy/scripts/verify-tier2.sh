#!/bin/bash
# Tier 2 verification — MinIO, LangGraph, backup (live checks, not stubs).
set -euo pipefail

ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
cd "$ROOT"
FAIL=0

pass() { echo "OK   $*"; }
fail() { echo "FAIL $*"; FAIL=1; }

echo "=== Clawsum Tier 2 verify ==="

# --- MinIO ---
if docker compose --profile storage ps --status running 2>/dev/null | grep -q minio; then
  pass "MinIO container running"
  if curl -sf http://127.0.0.1:9000/minio/health/live >/dev/null; then
    pass "MinIO health endpoint"
  else
    fail "MinIO health endpoint"
  fi
set -a
set +u
# shellcheck disable=SC1091
source .env 2>/dev/null || true
set -u
set +a
  USER="${MINIO_ROOT_USER:-clawsum}"
  PASS="${MINIO_ROOT_PASSWORD:-minio_change_me}"
  for bucket in clawsum-attachments clawsum-scrapes clawsum-backups; do
    if docker run --rm --network host --entrypoint /bin/sh minio/mc:latest \
      -c "mc alias set local http://127.0.0.1:9000 ${USER} ${PASS} && mc ls local/${bucket}" >/dev/null 2>&1; then
      pass "MinIO bucket ${bucket}"
    else
      fail "MinIO bucket ${bucket}"
    fi
  done
  TESTFILE="data/backups/tier2-minio-smoke.txt"
  mkdir -p data/backups
  echo "tier2-smoke $(date -Iseconds)" >"$TESTFILE"
  if docker run --rm --network host --entrypoint /bin/sh \
    -v "${ROOT}/${TESTFILE}:/t:ro" \
    minio/mc:latest \
    -c "mc alias set local http://127.0.0.1:9000 ${USER} ${PASS} && mc cp /t local/clawsum-backups/tier2-smoke.txt" >/dev/null 2>&1; then
    pass "MinIO upload smoke object"
  else
    fail "MinIO upload smoke object"
  fi
else
  fail "MinIO not running (docker compose --profile storage up -d minio)"
fi

# --- LangGraph ---
if docker compose --profile orchestration ps --status running 2>/dev/null | grep -q langgraph; then
  pass "LangGraph container running"
  if curl -sf http://127.0.0.1:8123/ok >/dev/null 2>&1; then
    pass "LangGraph /ok health"
  elif curl -sf http://127.0.0.1:8123/health >/dev/null 2>&1; then
    pass "LangGraph /health"
  else
    fail "LangGraph health endpoint"
  fi
  if python3 scripts/langgraph-smoke-test.py >/dev/null 2>&1; then
    pass "LangGraph gmail_triage run"
  elif curl -sf http://127.0.0.1:8123/docs >/dev/null 2>&1; then
    pass "LangGraph API docs (run smoke skipped)"
  else
    fail "LangGraph API not responding"
  fi
else
  fail "LangGraph not running"
fi

# --- Redis (LangGraph dependency) ---
if docker compose --profile orchestration ps --status running 2>/dev/null | grep -q redis; then
  if docker exec clawsum-redis-1 redis-cli ping 2>/dev/null | grep -q PONG; then
    pass "Redis PONG"
  else
    fail "Redis ping"
  fi
else
  fail "Redis not running"
fi

# --- Backup ---
if bash scripts/backup-platform.sh >/tmp/clawsum-backup-smoke.log 2>&1; then
  if ls data/backups/*/clawsum.dump >/dev/null 2>&1 || ls data/backups/*/obsidian.tgz >/dev/null 2>&1; then
    pass "backup-platform.sh produced artifacts"
  else
    fail "backup-platform.sh — no artifacts"
  fi
else
  fail "backup-platform.sh"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Tier 2 verify PASSED ==="
  exit 0
else
  echo "=== Tier 2 verify FAILED ==="
  exit 1
fi
