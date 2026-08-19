from pathlib import Path

voice = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/voice.py").read_text()
# find voice off / enable / toggle
for needle in ("voice off", "Voice off", "voice_mode", "enable_voice", "/voice", "VOICE_MODE"):
    idx = 0
    n = 0
    while n < 4:
        i = voice.find(needle, idx)
        if i < 0:
            break
        print(f"\n--- voice.py {needle} @{i} ---")
        print(voice[max(0,i-150):i+350])
        idx = i + len(needle)
        n += 1

cfg = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/config.py").read_text()
for needle in ("VOICE_TOOLS", "voice:", "tts:", "stt:", '"voice"'):
    i = cfg.find(needle)
    if i >= 0:
        print(f"\n--- config.py {needle} ---")
        print(cfg[max(0,i-100):i+400])

# tools config
tc = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/tools_config.py").read_text()
i = tc.find("VOICE_TOOLS")
print("\n--- tools_config VOICE ---")
print(tc[max(0,i-80):i+500] if i>=0 else "none")

# show hermes config check for voice-related defaults after migrate
import subprocess, os
os.environ["PATH"] = "/paperclip/.hermes-venv/bin:" + os.environ.get("PATH","")
r = subprocess.run(["hermes","config","check"], capture_output=True, text=True)
print("check stdout:\n", r.stdout[-2000:])
print("check stderr:\n", r.stderr[-1000:])
