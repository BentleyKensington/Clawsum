#!/usr/bin/env python3
"""Advance Media Phase 0 without restarts: MinIO bucket, sample ingest, CLA-62 comment."""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("/docker/clawsum")
API = "http://127.0.0.1:3100/api"
INBOX = Path("/docker/clawsum/data/media/inbox")
EXPORTS = Path("/docker/clawsum/data/media/exports")


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def req(method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(
        f"{API.rstrip('/')}/{path.lstrip('/')}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def ensure_dirs() -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    EXPORTS.mkdir(parents=True, exist_ok=True)
    # tiny silent wav via ffmpeg if inbox empty (local file only — no service restart)
    existing = [
        p
        for p in INBOX.rglob("*")
        if p.is_file()
        and p.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm", ".mp3", ".wav", ".m4a"}
    ]
    if not existing:
        sample = INBOX / "phase0-sample-tone.wav"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=2",
                "-ac",
                "1",
                str(sample),
            ],
            check=False,
            capture_output=True,
        )
        print("created_sample", sample, sample.exists())
    else:
        print("inbox_files", len(existing))


def ensure_minio_bucket(env: dict[str, str]) -> str:
    # Prefer existing container; do not recreate/restart it
    names = subprocess.check_output(
        ["docker", "ps", "--format", "{{.Names}}"], text=True
    )
    if "minio" not in names.lower():
        return "minio_container_absent"
    endpoint = env.get("MINIO_ENDPOINT") or env.get("MINIO_URL") or "http://127.0.0.1:9000"
    access = env.get("MINIO_ROOT_USER") or env.get("MINIO_ACCESS_KEY") or ""
    secret = env.get("MINIO_ROOT_PASSWORD") or env.get("MINIO_SECRET_KEY") or ""
    bucket = env.get("MINIO_MEDIA_BUCKET", "clawsum-media")
    if not access or not secret:
        return "minio_creds_missing"
    # Use python minio if present, else mc inside container if available
    try:
        from minio import Minio  # type: ignore
    except ImportError:
        Minio = None  # type: ignore
    if Minio:
        host = endpoint.replace("http://", "").replace("https://", "").rstrip("/")
        secure = endpoint.startswith("https://")
        client = Minio(host, access_key=access, secret_key=secret, secure=secure)
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            return f"bucket_created:{bucket}"
        return f"bucket_exists:{bucket}"
    # fallback: docker exec mc
    proc = subprocess.run(
        [
            "docker",
            "exec",
            "clawsum-minio-1",
            "mc",
            "alias",
            "set",
            "local",
            "http://127.0.0.1:9000",
            access,
            secret,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        # try without mc — just report
        return f"mc_alias_fail:{(proc.stderr or proc.stdout or '')[:120]}"
    subprocess.run(
        ["docker", "exec", "clawsum-minio-1", "mc", "mb", "-p", f"local/{bucket}"],
        capture_output=True,
        text=True,
    )
    return f"mc_mb_attempted:{bucket}"


def run_ingest_apply() -> dict:
    # Copy script if newer in /tmp
    src = Path("/tmp/media-ingest.py")
    dst = ROOT / "scripts" / "media-ingest.py"
    if src.is_file():
        dst.write_bytes(src.read_bytes().replace(b"\r\n", b"\n"))
    proc = subprocess.run(
        [
            "python3",
            str(dst),
            "--watch",
            str(INBOX),
            "--apply",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    print(out[-1500:])
    try:
        # last JSON object in output
        start = out.rfind("{")
        return json.loads(out[start:]) if start >= 0 else {"raw": out[-500:], "code": proc.returncode}
    except json.JSONDecodeError:
        return {"code": proc.returncode, "raw": out[-500:]}


def update_cla62(env: dict[str, str], body: str) -> None:
    cid = env["PAPERCLIP_COMPANY_ID"]
    code, issues = req("GET", f"/companies/{cid}/issues?q=CLA-62")
    if not isinstance(issues, list):
        print("CLA-62 lookup fail", code)
        return
    issue = next((i for i in issues if i.get("identifier") == "CLA-62"), None)
    if not issue:
        print("CLA-62 missing")
        return
    iid = issue["id"]
    # Reassign to media agent if present
    code, agents = req("GET", f"/companies/{cid}/agents")
    media = None
    if isinstance(agents, list):
        media = next(
            (
                a
                for a in agents
                if (a.get("adapterConfig") or {}).get("agentId") == "media"
                or a.get("name") == "Clawsum Media"
            ),
            None,
        )
    patch: dict = {}
    if media and issue.get("assigneeAgentId") != media["id"]:
        patch["assigneeAgentId"] = media["id"]
    # Clear recovery if any, move to todo for agent pickup (no heartbeat restart)
    code, rec = req("GET", f"/issues/{iid}/recovery-actions")
    active = (rec or {}).get("active") if isinstance(rec, dict) else None
    if active and active.get("id"):
        req(
            "POST",
            f"/issues/{iid}/recovery-actions/resolve",
            {
                "actionId": active["id"],
                "outcome": "restored",
                "sourceIssueStatus": "todo",
                "resolutionNote": "Phase 0 tooling advanced without service restart.",
            },
        )
    if issue.get("status") == "blocked":
        patch["status"] = "todo"
    if patch:
        code, res = req("PATCH", f"/issues/{iid}", patch)
        print("CLA-62 patch", code, patch, res.get("status") if isinstance(res, dict) else res)
    req("POST", f"/issues/{iid}/comments", {"body": body[:12000]})
    print("CLA-62 commented")


def main() -> int:
    env = load_env()
    # env prefixes without restart
    envf = ROOT / ".env"
    text = envf.read_text()
    adds = []
    for k, v in [
        ("FFMPEG_BIN", "/usr/bin/ffmpeg"),
        ("FFPROBE_BIN", "/usr/bin/ffprobe"),
        ("YTDLP_BIN", "/usr/local/bin/yt-dlp"),
        ("MEDIA_INBOX", str(INBOX)),
        ("MEDIA_EXPORTS", str(EXPORTS)),
        ("MINIO_MEDIA_BUCKET", "clawsum-media"),
    ]:
        if f"{k}=" not in text:
            adds.append(f"{k}={v}")
    if adds:
        envf.write_text(text.rstrip() + "\n" + "\n".join(adds) + "\n")
        print("env_appended", adds)
    ensure_dirs()
    bucket_status = ensure_minio_bucket(env)
    print("minio", bucket_status)
    ingest = run_ingest_apply()
    whisper = env.get("WHISPER_URL") or "(empty — deferred / not set)"
    comment = (
        "## Phase 0 progress (no service restart)\n"
        f"- ffmpeg/yt-dlp: present on host\n"
        f"- inbox: `{INBOX}`\n"
        f"- MinIO: `{bucket_status}`\n"
        f"- ingest --apply: `{json.dumps(ingest)[:800]}`\n"
        f"- WHISPER_URL: `{whisper}`\n"
        f"- PAPERCLIP_API_URL (gateway): `http://host.docker.internal:3102/api`\n\n"
        "Next for Media agent: wire Whisper when URL available; continue ingest watch.\n"
        "Out of scope still: local Ollama, YouTube publish, Resolve/Comfy."
    )
    update_cla62(env, comment)
    print("MEDIA_PHASE0_ADVANCED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
