#!/usr/bin/env bash
set -euo pipefail
ROOT=/docker/clawsum
echo "=== containers ==="
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'clawsum-|openclaw|paperclip|arcade|minio|grafana|prom|blackbox' | sort

echo "=== .env secret presence (no values) ==="
for k in CLOSEBOT_API_KEY X_CB_KEY ELEVENLABS_API_KEY ELEVENLABS_VOICE_ID OPENAI_API_KEY ARCADEDB_ROOT_PASSWORD MINIO_ROOT_PASSWORD GMAIL_REFRESH_TOKEN OPENCLAW_GATEWAY_TOKEN; do
  if grep -qE "^${k}=.+" "$ROOT/.env" 2>/dev/null; then
    len=$(grep -E "^${k}=" "$ROOT/.env" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | wc -c)
    echo "SET  $k (chars≈$((len-1)))"
  else
    echo "MISS $k"
  fi
done

echo "=== closebot skill paths ==="
ls -la "$ROOT/data/.openclaw/workspace/skills/closebot-api-operator/SKILL.md" 2>/dev/null && echo OK_OC_SKILL || echo MISS_OC_SKILL
ls -la "$ROOT/paperclip-data/.hermes/skills/integrations/closebot-api-operator/SKILL.md" 2>/dev/null && echo OK_HERMES_SKILL || echo MISS_HERMES_SKILL
docker exec clawsum-openclaw-gateway-1 ls /home/node/.openclaw/workspace/skills/closebot-api-operator/SKILL.md 2>/dev/null && echo OK_IN_GATEWAY || echo MISS_IN_GATEWAY

echo "=== gateway env (nonempty?) ==="
docker exec clawsum-openclaw-gateway-1 python3 -c '
import os
for k in ("CLOSEBOT_API_KEY","X_CB_KEY","ELEVENLABS_API_KEY","OPENAI_API_KEY"):
  v=os.environ.get(k) or ""
  print(("SET" if len(v)>8 else "EMPTY"), k, "len", len(v))
'

echo "=== closebot API ping (agency/current) ==="
docker exec clawsum-openclaw-gateway-1 python3 /home/node/.openclaw/workspace/skills/closebot-api-operator/scripts/closebot_request.py GET /agency/current 2>&1 | head -30

echo "=== docs ETL / arcade / media ==="
set -a; set +u; . "$ROOT/.env"; set -u; set +a
docker exec -i clawsum-postgres-1 psql -U "${POSTGRES_USER:-clawsum}" -d "${POSTGRES_DB:-clawsum}" -tAc \
  "SELECT 'people='||count(*) FROM ops.people; SELECT 'docs='||count(*) FROM ops.documents; SELECT 'chunks='||count(*) FROM ops.document_chunks; SELECT 'media='||count(*) FROM ops.media_objects; SELECT 'calls='||count(*) FROM ops.call_recordings; SELECT 'jarvis='||count(*) FROM ops.jarvis_processes;"

echo "=== tts / session-startup ==="
TOKEN=$(tr -d '\r\n' < "$ROOT/paperclip-data/.hermes/dashboard-session.token" 2>/dev/null || true)
curl -sS -H "X-Hermes-Session-Token: $TOKEN" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/tts/status; echo
curl -sS -H "X-Hermes-Session-Token: $TOKEN" http://127.0.0.1:9119/api/plugins/clawsum-cockpit/session-startup | python3 -c 'import sys,json; d=json.load(sys.stdin); print("startup_ok",d.get("ok"),"insight_len",len(d.get("insight_md") or ""))'

echo "=== public probes ==="
curl -sS 'http://127.0.0.1:9090/api/v1/query?query=probe_success{job="clawsum-public"}' | python3 -c 'import sys,json; 
for r in json.load(sys.stdin).get("data",{}).get("result",[]):
  m=r["metric"]; print(m.get("service"), r["value"][1])'

echo DONE
