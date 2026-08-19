#!/usr/bin/env bash
# Build + install Clawsum sidebar plugins (Inbox/Agents/Skills) + rebrand Hermes Agent title.
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SRC="${ROOT}/examples/hermes-cockpit"
CONTAINER="${PAPERCLIP_CONTAINER:-clawsum-paperclip-1}"
SHARED="${SRC}/plugin/_shared/clawsum-panels.js"
CSS="${SRC}/plugin/clawsum-cockpit/dashboard/dist/style.css"
H=/paperclip/.hermes

build_one() {
  local name="$1"
  local dir="${SRC}/plugin/${name}/dashboard"
  mkdir -p "${dir}/dist"
  cat "${SHARED}" "${dir}/dist/entry.js" > "${dir}/dist/index.js"
  cp -f "${CSS}" "${dir}/dist/style.css"
  echo "built ${name} ($(wc -c < "${dir}/dist/index.js") bytes)"
}

echo "== sync authority.json from skills + agents =="
python3 "${ROOT}/scripts/sync-cockpit-authority.py" || true

echo "== build plugin bundles =="
build_one clawsum-inbox
build_one clawsum-agents
build_one clawsum-skills
build_one clawsum-cron
build_one clawsum-kanban

# Ensure cockpit authority + API + CSS synced from examples
mkdir -p "${SRC}/plugin/clawsum-cockpit/dashboard/dist"
cp -f "${SRC}/plugin/clawsum-cockpit/dashboard/authority.json" \
  "${SRC}/plugin/clawsum-cockpit/dashboard/authority.json" 2>/dev/null || true

echo "== install cockpit theme =="
docker exec -u root "${CONTAINER}" mkdir -p "${H}/dashboard-themes"
docker cp "${SRC}/theme/clawsum-command.yaml" "${CONTAINER}:${H}/dashboard-themes/clawsum-command.yaml"
if [[ -f "${SRC}/skins/clawsum.yaml" ]]; then
  docker exec -u root "${CONTAINER}" mkdir -p "${H}/skins"
  docker cp "${SRC}/skins/clawsum.yaml" "${CONTAINER}:${H}/skins/clawsum.yaml" 2>/dev/null || true
fi

echo "== install plugins into Hermes home =="
docker exec -u root "${CONTAINER}" mkdir -p "${H}/plugins"
for name in clawsum-cockpit clawsum-inbox clawsum-agents clawsum-skills clawsum-cron clawsum-kanban; do
  docker exec -u root "${CONTAINER}" rm -rf "${H}/plugins/${name}"
  docker cp "${SRC}/plugin/${name}" "${CONTAINER}:${H}/plugins/${name}"
done
# shared panels already baked into inbox/agents/skills bundles; cockpit uses its own index.js

# cockpit assets + persona + company pack
docker exec -u root "${CONTAINER}" mkdir -p "${H}/plugins/clawsum-cockpit/dashboard/assets"
docker cp "${SRC}/assets/." "${CONTAINER}:${H}/plugins/clawsum-cockpit/dashboard/assets/" 2>/dev/null || true

# runtime env for inbox/approvals DB
if [[ -f "${ROOT}/paperclip-data/.hermes/clawsum-runtime.env" ]]; then
  docker cp "${ROOT}/paperclip-data/.hermes/clawsum-runtime.env" \
    "${CONTAINER}:${H}/clawsum-runtime.env"
  docker cp "${ROOT}/paperclip-data/.hermes/clawsum-runtime.env" \
    "${CONTAINER}:${H}/plugins/clawsum-cockpit/dashboard/clawsum-runtime.env"
fi

if [[ -f "${ROOT}/scripts/deploy-hermes-persona.sh" ]]; then
  bash "${ROOT}/scripts/deploy-hermes-persona.sh" || true
fi
if [[ -f "${ROOT}/scripts/seed-clawsum-company-pack.sh" ]]; then
  bash "${ROOT}/scripts/seed-clawsum-company-pack.sh" || true
fi

echo "== enable plugins + skin =="
docker exec -u root "${CONTAINER}" bash -lc '
export PATH=/paperclip/.hermes-venv/bin:$PATH
python3 - <<PY
from pathlib import Path
import yaml
p=Path("/paperclip/.hermes/config.yaml")
data=yaml.safe_load(p.read_text()) if p.exists() else {}
if not isinstance(data, dict): data={}
dash=data.setdefault("dashboard", {})
if not isinstance(dash, dict):
  dash={}; data["dashboard"]=dash
dash["theme"]="clawsum-command"
disp=data.setdefault("display", {})
if not isinstance(disp, dict):
  disp={}; data["display"]=disp
disp["skin"]="clawsum"
pl=data.setdefault("plugins", {})
if not isinstance(pl, dict):
  pl={}; data["plugins"]=pl
en=pl.get("enabled")
if not isinstance(en, list):
  en=[]; pl["enabled"]=en
for n in ["clawsum-cockpit","clawsum-inbox","clawsum-agents","clawsum-skills","clawsum-cron","clawsum-kanban"]:
  if n not in en: en.append(n)
dis = pl.get("disabled")
if not isinstance(dis, list):
  dis=[]; pl["disabled"]=dis
for n in ["kanban"]:
  if n not in dis: dis.append(n)
  if n in en: en.remove(n)
p.write_text(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))
print(p.read_text())
PY
'

echo "== patch web UI title Hermes Agent -> Clawsum Agent =="
docker exec -u root "${CONTAINER}" bash -lc '
python3 - <<PY
from pathlib import Path
html = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_dist/index.html")
t = html.read_text()
t2 = t.replace("Hermes Agent - Dashboard", "Clawsum Agent").replace("Hermes Agent", "Clawsum Agent")
if t2 != t:
  html.write_text(t2)
  print("patched index.html")
else:
  print("index.html already patched or pattern missing")
assets = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_dist/assets")
for js in assets.glob("index-*.js"):
  raw = js.read_text(errors="ignore")
  new = raw.replace("Hermes Agent", "Clawsum Agent")
  if new != raw:
    n = raw.count("Hermes Agent")
    js.write_text(new)
    print(f"patched {js.name}: Hermes Agent -> Clawsum Agent ({n} occurrences)")
  else:
    print(f"no Hermes Agent in {js.name}")
PY
'

echo "== restart dashboard =="
bash "${ROOT}/scripts/hermes-dashboard.sh" stop || true
sleep 1
bash "${ROOT}/scripts/hermes-dashboard.sh" start
sleep 2
curl -sS http://127.0.0.1:9119/api/dashboard/plugins | python3 -c "import sys,json; print([p['name']+':'+p.get('label','') for p in json.load(sys.stdin)])"
echo DONE
