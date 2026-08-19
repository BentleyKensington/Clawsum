from pathlib import Path
import re

# Search config schema / defaults for voice
roots = [
    Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli"),
    Path("/paperclip/.hermes-venv/lib/python3.13/site-packages"),
]
needles = ["voice off", "Voice off", "voice_mode", "voiceEnabled", "tts_enabled", "VOICE_TOOLS", "messages.tts", "stt_enabled"]
for root in roots[:1]:
    for p in root.rglob("*.py"):
        try:
            t = p.read_text(errors="ignore")
        except Exception:
            continue
        for n in needles:
            if n in t:
                print(f"{p}:{n}")

# web dist string
assets = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_dist/assets")
for f in assets.glob("index-*.js"):
    t = f.read_text(errors="ignore")
    for n in ["Voice off", "voice off", "Voice On", "voiceMode", "tts", "mic"]:
        i = t.find(n)
        if i >= 0:
            print("UI", n, "->", t[max(0,i-80):i+120].replace("\n"," ")[:200])

# hermes .env keys related
env = Path("/paperclip/.hermes/.env")
if env.exists():
    for line in env.read_text().splitlines():
        if any(x in line.upper() for x in ("VOICE", "TTS", "STT", "ELEVEN", "SPEECH", "OPENAI")):
            k = line.split("=",1)[0]
            print("ENV", k, "set" if "=" in line and line.split("=",1)[1].strip() else "empty")
