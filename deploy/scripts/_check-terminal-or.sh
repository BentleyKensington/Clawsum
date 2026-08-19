#!/usr/bin/env bash
set -euo pipefail
echo "=== root shell history: OPENROUTER / sk-or / .env edits ==="
grep -nE 'OPENROUTER|sk-or-v1|openrouter\.json|nano .*\.env|vim .*\.env|vi .*\.env' /root/.bash_history 2>/dev/null | sed -n '1,80p' || true
echo "=== fish/zsh if any ==="
grep -nE 'OPENROUTER|sk-or-v1' /root/.zsh_history /root/.local/share/fish/fish_history 2>/dev/null | sed -n '1,40p' || true
echo "=== screen/tmux scrollbacks? ==="
ls /tmp/tmux* /var/tmp/tmux* 2>/dev/null || true
echo "=== journal with openrouter (no secrets dump) ==="
journalctl --since '2026-05-01' 2>/dev/null | grep -i openrouter | sed -n '1,20p' || true
echo "=== last nano backup dirs ==="
find /root /tmp /docker/clawsum -name '*env*.save' -o -name '.env.save' -o -name '*env*.bak' 2>/dev/null | sed -n '1,30p'
