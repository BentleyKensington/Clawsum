from pathlib import Path

main = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/main.py").read_text()
ws = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_server.py").read_text()
print("main len", len(main))
for name in ("def _make_tui_argv", "def _ensure_tui_workspace", "def _restore_tui_workspace"):
    i = main.find(name)
    print("\n====", name, "idx", i, "====")
    if i >= 0:
        print(main[i : i + 2500])

for needle in ("Chat unavailable: the embedded terminal requires", "def _spawn_pty", "ui-tui", "tui_dist"):
    i = ws.find(needle)
    print("\n==== ws", needle, "idx", i, "====")
    if i >= 0:
        print(ws[max(0, i - 120) : i + 700])

# PROJECT_ROOT
i = main.find("PROJECT_ROOT")
print("\nPROJECT snippets:")
count = 0
start = 0
while count < 8:
    j = main.find("PROJECT_ROOT", start)
    if j < 0:
        break
    print(main[j : j + 120].replace("\n", " | "))
    start = j + 12
    count += 1

root = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages")
print("\nroot children with tui:", [p.name for p in root.iterdir() if "tui" in p.name.lower() or p.name == "ui-tui"])
td = root / "hermes_cli" / "tui_dist"
print("tui_dist", td.exists(), list(td.iterdir())[:5] if td.exists() else None)
