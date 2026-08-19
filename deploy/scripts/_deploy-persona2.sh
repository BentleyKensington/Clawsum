#!/usr/bin/env bash
set -euo pipefail
ST=/tmp/clawsum-persona2
ROOT=/docker/clawsum
C=clawsum-paperclip-1
EX="$ROOT/examples/hermes-cockpit"

for f in SOUL.md BOOT.md USER.md APPROVALS.md; do
  cp -f "$ST/$f" "$EX/$f"
  sed -i 's/\r$//' "$EX/$f"
  docker cp "$EX/$f" "$C:/paperclip/.hermes/$f"
  cp -f "$EX/$f" "$ROOT/paperclip-data/.hermes/$f" 2>/dev/null || true
done

cp -f "$ST/COMPANY.md" "$ROOT/personas/clawsum/COMPANY.md" 2>/dev/null || mkdir -p "$ROOT/personas/clawsum" && cp -f "$ST/COMPANY.md" "$ROOT/personas/clawsum/COMPANY.md"
sed -i 's/\r$//' "$ROOT/personas/clawsum/COMPANY.md"

cp -f "$ST/index.js" "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js"
cp -f "$ST/style.css" "$EX/plugin/clawsum-cockpit/dashboard/dist/style.css"
sed -i 's/\r$//' "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js" "$EX/plugin/clawsum-cockpit/dashboard/dist/style.css"
docker cp "$EX/plugin/clawsum-cockpit/dashboard/dist/index.js" "$C:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js"
docker cp "$EX/plugin/clawsum-cockpit/dashboard/dist/style.css" "$C:/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/style.css"

# Seed owner identity into MEMORY tip if missing
python3 - <<'PY'
from pathlib import Path
p = Path("/docker/clawsum/paperclip-data/.hermes/MEMORY.md")
text = p.read_text(encoding="utf-8") if p.exists() else "# MEMORY.md\n"
needle = "Hennessey Holdings LLC"
if needle not in text:
    block = (
        "\n## Owner identity\n"
        "- Holding: **Hennessey Holdings LLC**\n"
        "- Master Boss: **Gerald Allan Hennessey**\n"
        "- Ops brand: Clawsum\n"
    )
    p.write_text(text.rstrip() + "\n" + block + "\n", encoding="utf-8")
    print("MEMORY.md updated")
else:
    print("MEMORY.md already has holding")
PY
docker cp "$ROOT/paperclip-data/.hermes/MEMORY.md" "$C:/paperclip/.hermes/MEMORY.md" 2>/dev/null || true

bash "$ROOT/scripts/force-restart-hermes-dashboard.sh"
echo "=== checks ==="
docker exec "$C" grep -c "Hennessey Holdings\|plan table first\|One box for voice" /paperclip/.hermes/SOUL.md /paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/index.js
echo DONE
