#!/usr/bin/env bash
# Give dinohawk a writable Dino Crush tree + apply_patch + apply watcher.
set -euo pipefail
CLAWSUM_DIR="${CLAWSUM_DIR:-/docker/clawsum}"
OC="${CLAWSUM_DIR}/data/.openclaw"
WS="${OC}/workspace-dinohawk"
TPL="${CLAWSUM_DIR}/templates/dinohawk"
[[ -d "$TPL" ]] || TPL="${CLAWSUM_DIR}/deploy/templates/dinohawk"
mkdir -p "$WS"
if [[ -f "$TPL/GAME.md" ]]; then
  cp -f "$TPL/GAME.md" "$WS/GAME.md"
fi
if [[ -f "$TPL/OBSIDIAN.md" && ! -f "$WS/OBSIDIAN.md" ]]; then
  cp -f "$TPL/OBSIDIAN.md" "$WS/OBSIDIAN.md"
fi
if [[ ! -f "$WS/AGENTS.md" ]]; then
  cat > "$WS/AGENTS.md" <<'EOF'
# AGENTS.md — dinohawk

## Tool access

- Allowed: read, write, edit, apply_patch, browser, exec
- Denied: (none)

## Rules

- Stay inside this workspace unless Boss explicitly redirects.
- Dino Crush play lives in `game/`. Patch those files, then `touch game/.apply-request`.
- Use Obsidian only in the folder named in OBSIDIAN.md.
- Never print CLOSEBOT_API_KEY, EBAY_CLIENT_SECRET, or DINOCRUSHBOSS_PLAY_PASSWORD.
EOF
fi
if [[ -f "$WS/SOUL.md" ]] && ! grep -q 'game/\.apply-request' "$WS/SOUL.md"; then
  printf '\n\nYou edit Dino Crush play under `game/`. After a playable patch: `touch game/.apply-request`. See GAME.md.\n' >> "$WS/SOUL.md"
fi
chown -R 1000:1000 "$WS" 2>/dev/null || true

python3 - <<'PY'
import json
from pathlib import Path
p = Path("/docker/clawsum/data/.openclaw/openclaw.json")
cfg = json.loads(p.read_text(encoding="utf-8"))
want = {
    "allow": ["read", "write", "edit", "apply_patch", "browser", "exec"],
    "deny": [],
}
changed = False
for agent in cfg.setdefault("agents", {}).setdefault("list", []):
    if agent.get("id") != "dinohawk":
        continue
    agent["workspace"] = "/home/node/.openclaw/workspace-dinohawk"
    if agent.get("tools") != want:
        agent["tools"] = want
        changed = True
    print("dinohawk tools", json.dumps(agent.get("tools")))
    break
else:
    raise SystemExit("dinohawk agent missing from openclaw.json")
if changed:
    p.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print("openclaw.json updated")
else:
    print("openclaw.json already current")
PY

# Bind-mount game into the dinohawk workspace.
COMPOSE="${CLAWSUM_DIR}/docker-compose.yml"
if [[ -f "$COMPOSE" ]]; then
  python3 - <<'PY'
from pathlib import Path
p = Path("/docker/clawsum/docker-compose.yml")
text = p.read_text(encoding="utf-8")
needle = "      - ./modules/dinocrushboss:/home/node/.openclaw/workspace-dinohawk/game"
if needle not in text:
    old = "      - ./bin/gog:/usr/local/bin/gog:ro"
    if old in text:
        text = text.replace(old, old + "\n" + needle, 1)
        p.write_text(text, encoding="utf-8")
        print("compose volume added")
    else:
        print("WARN: could not insert game volume into compose")
else:
    print("compose volume already present")
PY
  (cd "$CLAWSUM_DIR" && docker compose up -d openclaw-gateway) || true
fi

bash "${CLAWSUM_DIR}/scripts/start-dinocrushboss-apply-watcher.sh" 2>/dev/null || \
  bash "${CLAWSUM_DIR}/deploy/scripts/start-dinocrushboss-apply-watcher.sh"

echo "DINOHAWK_GAME_WIRED $WS"
