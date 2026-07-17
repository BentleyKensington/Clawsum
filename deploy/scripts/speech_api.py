#!/usr/bin/env python3
"""
On-demand speech API — STT and TTS via OpenAI, ElevenLabs, or OpenRouter.

Examples:
  python3 speech_api.py stt --input recording.wav
  python3 speech_api.py tts --text "Hello Boss" --output reply.mp3
  python3 speech_api.py tts --text "Hi" --provider elevenlabs --output hi.mp3
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import llm_policy as policy

OPENAI_URL = policy.env_get("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
OPENROUTER_URL = policy.env_get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
ELEVENLABS_URL = policy.env_get("ELEVENLABS_API_BASE", "https://api.elevenlabs.io/v1").rstrip("/")


def _http(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: int = 120,
) -> bytes:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:500]}") from e


def stt_openai(path: Path) -> str:
    api_key = policy.env_get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY required for OpenAI STT")
    model = policy.env_get("OPENAI_STT_MODEL", "whisper-1")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    boundary = "----clawsumboundary"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="model"\r\n\r\n{model}\r\n'.encode(),
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
                f"Content-Type: {mime}\r\n\r\n"
            ).encode(),
            path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    raw = _http(
        f"{OPENAI_URL}/audio/transcriptions",
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        data=body,
    )
    return json.loads(raw.decode()).get("text", "")


def stt_openrouter(path: Path) -> str:
    """OpenRouter audio input — uses chat with input_audio (provider-dependent)."""
    api_key = policy.require_openrouter_key()
    model = policy.openrouter_api_model(
        policy.env_get("OPENROUTER_STT_MODEL", "google/gemini-2.5-flash")
    )
    audio_b64 = base64.standard_b64encode(path.read_bytes()).decode()
    mime = mimetypes.guess_type(path.name)[0] or "audio/wav"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Transcribe this audio verbatim."},
                    {
                        "type": "input_audio",
                        "input_audio": {"data": audio_b64, "format": mime.split("/")[-1]},
                    },
                ],
            }
        ],
    }
    raw = _http(
        f"{OPENROUTER_URL}/chat/completions",
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload).encode(),
    )
    data = json.loads(raw.decode())
    return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")


def tts_openai(text: str, output: Path) -> None:
    api_key = policy.env_get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY required for OpenAI TTS")
    payload = {
        "model": policy.env_get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        "voice": policy.env_get("OPENAI_TTS_VOICE", "alloy"),
        "input": text,
        "response_format": policy.env_get("OPENAI_TTS_FORMAT", "mp3"),
    }
    audio = _http(
        f"{OPENAI_URL}/audio/speech",
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload).encode(),
    )
    output.write_bytes(audio)


def tts_elevenlabs(text: str, output: Path) -> None:
    api_key = policy.env_get("ELEVENLABS_API_KEY")
    voice_id = policy.env_get("ELEVENLABS_VOICE_ID")
    if not api_key or not voice_id:
        raise SystemExit("ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID required")
    model = policy.env_get("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2")
    payload = {
        "text": text,
        "model_id": model,
    }
    audio = _http(
        f"{ELEVENLABS_URL}/text-to-speech/{voice_id}",
        method="POST",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        data=json.dumps(payload).encode(),
    )
    output.write_bytes(audio)


def cmd_stt(args: argparse.Namespace) -> None:
    path = Path(args.input)
    if not path.is_file():
        raise SystemExit(f"Missing audio file: {path}")
    provider = (args.provider or policy.speech_stt_provider()).lower()
    if provider == "openai":
        text = stt_openai(path)
    elif provider == "openrouter":
        text = stt_openrouter(path)
    else:
        raise SystemExit(f"Unsupported STT provider: {provider}")
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text)


def cmd_tts(args: argparse.Namespace) -> None:
    text = args.text
    if args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    if not text:
        raise SystemExit("--text or --input required")
    output = Path(args.output or "speech-out.mp3")
    provider = (args.provider or policy.speech_tts_provider()).lower()
    if provider == "openai":
        tts_openai(text, output)
    elif provider == "elevenlabs":
        tts_elevenlabs(text, output)
    else:
        raise SystemExit(f"Unsupported TTS provider: {provider}")
    print(f"OK wrote {output} ({output.stat().st_size} bytes)")


def main() -> None:
    p = argparse.ArgumentParser(description="Clawsum on-demand STT/TTS")
    sub = p.add_subparsers(dest="cmd", required=True)

    stt = sub.add_parser("stt", help="Speech-to-text")
    stt.add_argument("--input", required=True, help="Audio file path")
    stt.add_argument("--output", help="Write transcript to file")
    stt.add_argument("--provider", choices=["openai", "openrouter"])
    stt.set_defaults(func=cmd_stt)

    tts = sub.add_parser("tts", help="Text-to-speech")
    tts.add_argument("--text", help="Text to speak")
    tts.add_argument("--input", help="Read text from file")
    tts.add_argument("--output", help="Output audio path (default speech-out.mp3)")
    tts.add_argument("--provider", choices=["openai", "elevenlabs"])
    tts.set_defaults(func=cmd_tts)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
