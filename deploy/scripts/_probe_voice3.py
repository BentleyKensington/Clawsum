from pathlib import Path

# Search TUI + web for exact Voice off label
paths = list(Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/tui_dist").glob("*.js"))
paths += list(Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_dist/assets").glob("index-*.js"))
for f in paths:
    t = f.read_text(errors="ignore")
    for n in ["Voice off", "voice off", "Voice on", "Voice On", "voiceMode", "voice_mode", "Push to talk", "Listening"]:
        i = 0
        found = 0
        while found < 2:
            j = t.find(n, i)
            if j < 0:
                break
            print(f.name[:40], repr(n), "->", t[max(0,j-100):j+160].replace("\n"," ")[:220])
            i = j + len(n)
            found += 1

# Check if sounddevice / mic available in container
import subprocess
r = subprocess.run(["/paperclip/.hermes-venv/bin/python3","-c",
"import importlib\n"
"for m in ['sounddevice','soundfile','numpy']:\n"
"  try:\n"
"    importlib.import_module(m); print(m,'OK')\n"
"  except Exception as e:\n"
"    print(m,'FAIL',e)\n"
"try:\n"
"  import sounddevice as sd\n"
"  print('devices', sd.query_devices())\n"
"except Exception as e:\n"
"  print('devices_err',e)\n"
], capture_output=True, text=True)
print("AUDIO", r.stdout)
print(r.stderr[:500] if r.stderr else "")

# config defaults for voice/tts section from DEFAULT_CONFIG
cfg = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/config.py").read_text()
i = cfg.find('"tts"')
print("tts default block:\n", cfg[i:i+1200] if i>=0 else "none")
i = cfg.find('"voice"')
# find voice section in DEFAULT
import re
for m in re.finditer(r'["\']voice["\']\s*:\s*\{', cfg):
    print("voice block at", m.start())
    print(cfg[m.start():m.start()+800])
    break
