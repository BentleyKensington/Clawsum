from pathlib import Path
import importlib
import hermes_cli.main as m

print("find_bundled", getattr(m, "_find_bundled_tui", None))
if hasattr(m, "_find_bundled_tui"):
    print("bundled path:", m._find_bundled_tui())

# show function source-ish
src = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/main.py").read_text()
i = src.find("def _find_bundled_tui")
print(src[i:i+900] if i>=0 else "no find_bundled")

td = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/tui_dist")
print("tui_dist files:")
for p in sorted(td.iterdir()):
    print(" ", p.name, p.stat().st_size)
