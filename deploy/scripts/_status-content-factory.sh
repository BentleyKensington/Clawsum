#!/bin/bash
echo '=== procs ==='
ps aux | grep -E 'provision-content|seed-persona|content-factory|psql' | grep -v grep || true
echo '=== tables ==='
docker exec clawsum-postgres-1 psql -U clawsum -d clawsum -c "SELECT tablename FROM pg_tables WHERE schemaname='ops' AND (tablename LIKE 'content%' OR tablename='social_queue') ORDER BY 1;"
echo '=== cron ==='
cat /etc/cron.d/clawsum-content-factory 2>/dev/null || echo no-cron
echo '=== files ==='
ls -la /docker/clawsum/scripts/content-factory.py /docker/clawsum/docs/CONTENT-FACTORY.md 2>/dev/null || true
echo '=== ideas ==='
docker exec clawsum-postgres-1 psql -U clawsum -d clawsum -c "SELECT id, status, left(title,50) FROM ops.content_ideas ORDER BY created_at DESC LIMIT 5;" 2>/dev/null || true
