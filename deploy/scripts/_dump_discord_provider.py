from pathlib import Path
p = Path("/home/node/.openclaw/npm/projects/openclaw-discord-c0892df945/node_modules/@openclaw/discord/dist/provider-Cqe8M2zT.js")
print("exists", p.exists())
if not p.exists():
    raise SystemExit(1)
lines = p.read_text(errors="replace").splitlines()
# find the readiness string
for i, line in enumerate(lines):
    if "awaiting gateway readiness" in line:
        start = max(0, i - 40)
        end = min(len(lines), i + 60)
        for j in range(start, end):
            print(f"{j+1}:{lines[j]}")
        break
