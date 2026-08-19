#!/usr/bin/env python3
"""
Pre-generate ElevenLabs MP3s for approved Jarvis greetings + acks.

Stores under Hermes audio_cache so /tts can serve instantly (no live API wait).

  python3 /docker/clawsum/scripts/pregen-jarvis-greetings-tts.py
  python3 /docker/clawsum/scripts/pregen-jarvis-greetings-tts.py --force

Outputs:
  /docker/clawsum/paperclip-data/.hermes/audio_cache/greetings/<sha12>.mp3
  .../audio_cache/greetings/manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
ENV = ROOT / ".env"
POOL_CANDIDATES = [
    ROOT / "examples" / "hermes-cockpit" / "greetings.json",
    ROOT / "paperclip-data" / ".hermes" / "greetings.json",
    Path(__file__).resolve().parents[1] / "examples" / "hermes-cockpit" / "greetings.json",
]
CACHE_DIR = ROOT / "paperclip-data" / ".hermes" / "audio_cache" / "greetings"
# Also mirror into container mount path when present
CACHE_ALT = Path("/paperclip/.hermes/audio_cache/greetings")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            k, _, v = raw.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    out.update({k: v for k, v in os.environ.items() if v})
    # Hermes runtime env often has the key when host .env is not visible to paperclip
    for p in (
        ROOT / "paperclip-data" / ".hermes" / "clawsum-runtime.env",
        Path("/paperclip/.hermes/clawsum-runtime.env"),
    ):
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            k, _, v = raw.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and v and k not in out:
                out[k] = v
    return out


def slug(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:12]


def load_pool() -> dict[str, list[str]]:
    for p in POOL_CANDIDATES:
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            print(f"pool: {p}")
            return {
                "greetings": list(data.get("greetings") or []),
                "acks": list(data.get("acks") or []),
            }
    raise SystemExit("greetings.json not found")


def synthesize(text: str, env: dict[str, str]) -> bytes:
    key = (env.get("ELEVENLABS_API_KEY") or "").strip()
    if not key:
        raise SystemExit("ELEVENLABS_API_KEY missing")
    voice = (env.get("ELEVENLABS_VOICE_ID") or "KuQm0Vgf0XGL6Vqko2UY").strip()
    model = (env.get("ELEVENLABS_TTS_MODEL") or "eleven_multilingual_v2").strip()
    base = (env.get("ELEVENLABS_API_BASE") or "https://api.elevenlabs.io/v1").rstrip("/")
    body = json.dumps(
        {
            "text": text,
            "model_id": model,
            "voice_settings": {
                "stability": float(env.get("ELEVENLABS_STABILITY") or "0.45"),
                "similarity_boost": float(env.get("ELEVENLABS_SIMILARITY") or "0.8"),
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/text-to-speech/{voice}",
        data=body,
        method="POST",
        headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    env = load_env()
    pool = load_pool()
    lines: list[tuple[str, str]] = []
    for kind in ("greetings", "acks"):
        for t in pool[kind]:
            lines.append((kind, t.strip()))

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if CACHE_ALT.parent.exists():
        CACHE_ALT.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, dict] = {}
    ok = skip = fail = 0
    for kind, text in lines:
        sid = slug(text)
        out = CACHE_DIR / f"{sid}.mp3"
        if out.exists() and not args.force:
            skip += 1
            manifest[text] = {
                "id": sid,
                "kind": kind,
                "path": str(out),
                "url": f"/api/plugins/clawsum-cockpit/tts/cache/{sid}",
                "bytes": out.stat().st_size,
            }
            continue
        if args.dry_run:
            print(f"would generate [{kind}] {sid}: {text[:60]}")
            continue
        try:
            audio = synthesize(text, env)
            out.write_bytes(audio)
            if CACHE_ALT.parent.exists():
                (CACHE_ALT / f"{sid}.mp3").write_bytes(audio)
            manifest[text] = {
                "id": sid,
                "kind": kind,
                "path": str(out),
                "url": f"/api/plugins/clawsum-cockpit/tts/cache/{sid}",
                "bytes": len(audio),
            }
            ok += 1
            print(f"OK {kind} {sid} ({len(audio)} bytes) {text[:50]}")
            time.sleep(0.25)
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, OSError) as e:
            fail += 1
            print(f"FAIL {kind} {sid}: {e}", file=sys.stderr)

    man_path = CACHE_DIR / "manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if CACHE_ALT.parent.exists():
        (CACHE_ALT / "manifest.json").write_text(man_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"done ok={ok} skip={skip} fail={fail} manifest={man_path}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
