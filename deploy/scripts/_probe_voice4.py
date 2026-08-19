from pathlib import Path
t = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/tui_dist/entry.js").read_text(errors="ignore")
for n in ["/voice on", "/voice off", "/voice tts", "auto_tts", "Voice mode", "voiceMode", "toggleVoice", "startContinuous"]:
    i = t.find(n)
    if i >= 0:
        print(n, "->", t[max(0,i-60):i+180].replace("\n"," ")[:240])

# Does web UI have separate browser speechRecognition?
w = Path("/paperclip/.hermes-venv/lib/python3.13/site-packages/hermes_cli/web_dist/assets")
for f in w.glob("index-*.js"):
    s = f.read_text(errors="ignore")
    for n in ["SpeechRecognition", "webkitSpeechRecognition", "getUserMedia", "MediaRecorder", "auto_tts", "Voice off"]:
        i = s.find(n)
        if i >= 0:
            print("WEB", n, "->", s[max(0,i-40):i+120].replace("\n"," ")[:200])
