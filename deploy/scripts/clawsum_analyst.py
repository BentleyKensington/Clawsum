#!/usr/bin/env python3
"""
ChatGPT-style analyst for Boss material — email, images, repos, tasks.

Talk like a sharp colleague in a paste window: summary, take, whether it
matters to Gerald's work, how it compares, what to do next. No ticket jargon.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("CLAWSUM_ROOT", "/docker/clawsum"))
ENV_FILE = ROOT / ".env"
AUTHORITY = (
    ROOT / "paperclip-data/.hermes/plugins/clawsum-cockpit/dashboard/authority.json"
)
AUTHORITY_ALT = (
    ROOT / "examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/authority.json"
)

GITHUB_RE = re.compile(r"https?://github\.com/([^/\s)>\"]+)/([^/\s)>\"]+)", re.I)
GITLAB_RE = re.compile(r"https?://gitlab\.com/([^/\s)>\"]+)/([^/\s)>\"]+)", re.I)
IMAGE_KINDS = {"photo"}
IMAGE_CT = ("image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif")
ROBOTIC = (
    "sender appears to request attention",
    "cell=",
    "action_required=",
    "likely automated / marketing",
    "informational message tagged to cell",
    "hermes should ask boss",
)

SYSTEM = """You are Gerald's operator — same job as ChatGPT when he pastes something in.

Clawsum is meant to become the best ops platform by always improving. Hermes talks,
Paperclip tracks work, OpenClaw agents execute. Other cells: GHL/Closebot, Vocalitic,
roofing/RE, Techtasia, AcceptAI/FastBuy, media studio, local/self-hosted AI.

Philosophy (non-negotiable):
- Overlap is NOT a reason to dismiss. If a tool is resourceful, say HOW it overlaps
  (layer by layer: UI vs task board vs agent runtime vs skill factory vs memory),
  what it does better, what we do better, and whether to adopt, run side-by-side,
  steal the ideas into Clawsum, or skip as noise.
- Replacing or testing beside Hermes/OpenClaw/Paperclip is on the table when the
  new thing is clearly better at a job we care about.
- Every item MUST be assigned: a project slug AND an owner agent. Never leave orphan.
- Mockups / UI shots: say if Clawsum should adopt the look or flow. Treat design
  attachments as product input, not junk.
- When work is worth doing, name the skills/training agents need to execute it
  (existing skill ids or a new skill to forge).

Project slugs (pick one): clawsum-platform, personal-admin, wnn-client, vocalitic,
roofing-os, real-estate, techtasia, acceptai-fastbuy, hardware-local-ai, media-production.

Owner agents (pick one): Clawsum Admin, Clawsum, Clawsum Paperclip, Clawsum Coding,
Clawsum Data, Clawsum GHL, Clawsum RE, Clawsum Comms, Clawsum Research,
Clawsum Planning, Clawsum Media, Clawsum Pentest.

Rules:
- Plain English. Opinionated. Skip only true noise (noreply marketing, "finish Google setup").
- Always cover: what it is, take, project, owner, HOW it compares, adopt verdict, next moves.
- Self-hosted / GitHub: fetch-aware — use any README provided. Be specific.
- Images: describe them; flag mockups for Clawsum UI/UX adoption.
- Do not invent Paperclip IDs or pretend you clicked. No container/signal dumps.

Return STRICT JSON with keys:
  summary (2–4 sentences),
  take (honest opinion),
  project_fit (human sentence),
  project_slug (one slug from the list),
  owner_agent (one agent from the list),
  vs_what_we_have (HOW it overlaps / differs — not "we already have agents"),
  adopt_verdict (adopt|side_by_side|steal_ideas|skip_noise),
  mockup_adopt (string; what UI/flow to steal, or empty),
  skills_needed (array of skill ids or short new-skill names),
  suggestions (array of next moves),
  skip (bool; true ONLY for skip_noise),
  priority (urgent|high|medium|low|noise),
  review_status (needs_boss|reviewed|ignored),
  action_required (bool),
  questions_for_boss (array; when anything is unclear, 1–3 *leading* questions
    that suggest a better Clawsum — e.g. "Stand this up side-by-side this week,
    or steal just the skill-factory pattern first?" Not interrogation.),
  image_notes (string),
  repo_notes (string),
  report_markdown (full brief with headings: What this is / My take / Owner /
    How it compares / Adopt or not / Images / Skills to grow / What I'd do)
"""


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            k, _, v = raw.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        if v:
            out.setdefault(k, v)
    return out


def is_robotic_report(text: str | None, analysis_json: dict | None = None) -> bool:
    if isinstance(analysis_json, dict) and analysis_json.get("style") == "chatgpt":
        return False
    blob = (text or "").lower()
    return any(s in blob for s in ROBOTIC)


def _authority() -> dict:
    for p in (AUTHORITY, AUTHORITY_ALT):
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
    return {}


def enterprise_snapshot(cur=None) -> dict[str, Any]:
    cells: list[dict] = []
    people: list[dict] = []
    if cur is not None:
        try:
            cur.execute(
                "SELECT slug, name, type FROM ops.businesses WHERE active ORDER BY slug LIMIT 40"
            )
            cells = [dict(r) for r in cur.fetchall()]
        except Exception:
            pass
        try:
            cur.execute(
                """
                SELECT display_name, kind, company_name
                FROM ops.people WHERE active
                ORDER BY kind, display_name LIMIT 40
                """
            )
            people = [dict(r) for r in cur.fetchall()]
        except Exception:
            pass
    auth = _authority()
    agents = [
        {"id": a.get("id"), "name": a.get("name"), "domains": a.get("domains")}
        for a in (auth.get("agents") or [])[:16]
        if isinstance(a, dict)
    ]
    return {
        "projects": cells
        or [
            {"slug": "clawsum-platform", "name": "Clawsum"},
            {"slug": "wnn-client", "name": "GHL / Closebot"},
            {"slug": "vocalitic", "name": "Vocalitic"},
            {"slug": "roofing-os", "name": "Roofing / storm"},
            {"slug": "real-estate", "name": "Real estate"},
            {"slug": "techtasia", "name": "Techtasia"},
            {"slug": "acceptai-fastbuy", "name": "AcceptAI / FastBuy"},
            {"slug": "hardware-local-ai", "name": "Local / self-hosted AI"},
        ],
        "people_sample": people[:20],
        "agents": agents,
        "stack_notes": (
            "Clawsum layers: Hermes = CEO chat/UI; Paperclip = board/approvals; "
            "OpenClaw = agent runtime; skills in deploy/skills/*. "
            "We do NOT auto-dismiss overlap. Example: RevFactory Harness is a "
            "Claude-Code skill factory (domain sentence → agent md + skills + 6 "
            "team patterns). That is NOT the same as Hermes UI or OpenClaw runtime. "
            "If something is better at a layer, recommend adopt or side-by-side."
        ),
    }


def _http_json(url: str, payload: dict, headers: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


DEEP_CUES = (
    "github.com",
    "gitlab.com",
    "compare",
    " vs ",
    "research",
    "architecture",
    "adopt",
    "harness",
    "self-hosted",
    "open source",
    "open-source",
    "benchmark",
    "side-by-side",
    "side by side",
    "how does",
    "mockup",
)


def archive_keywords(text: str, *, limit: int = 8) -> list[str]:
    stop = {
        "this", "that", "with", "from", "your", "have", "been", "will", "what",
        "when", "they", "them", "just", "into", "about", "http", "https", "www",
        "com", "the", "and", "for", "you",
    }
    words: list[str] = []
    for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text or ""):
        lw = w.lower()
        if lw in stop or lw in words:
            continue
        words.append(lw)
        if len(words) >= limit:
            break
    return words


def consult_archive(cur, query_text: str, *, limit: int = 6) -> list[dict]:
    """Pull related ChatGPT-archive + memory facts. Skips personal."""
    if cur is None:
        return []
    keys = archive_keywords(query_text)
    if not keys:
        return []
    likes = [f"%{k}%" for k in keys[:6]]
    hits: list[dict] = []
    try:
        cur.execute(
            """
            SELECT c.title,
                   COALESCE(NULLIF(c.intent_summary,''), NULLIF(c.summary,''), '') AS blurb,
                   c.scope, c.work_status, c.topics
            FROM ops.conversations c
            WHERE COALESCE(c.scope, 'unknown') <> 'personal'
              AND (
                c.title ILIKE ANY(%s)
                OR COALESCE(c.summary,'') ILIKE ANY(%s)
                OR COALESCE(c.intent_summary,'') ILIKE ANY(%s)
              )
            ORDER BY c.updated_at_source DESC NULLS LAST
            LIMIT %s
            """,
            (likes, likes, likes, limit),
        )
        for r in cur.fetchall():
            d = dict(r)
            hits.append(
                {
                    "source": "chatgpt_archive",
                    "title": d.get("title"),
                    "blurb": (d.get("blurb") or "")[:400],
                    "scope": d.get("scope"),
                    "status": d.get("work_status"),
                }
            )
    except Exception as exc:
        print(f"WARN: archive consult conversations: {exc}", flush=True)
    try:
        cur.execute(
            """
            SELECT fact_text, fact_type
            FROM ops.extracted_facts
            WHERE COALESCE(approved_for_hermes_memory, false) = true
              AND fact_text ILIKE ANY(%s)
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (likes, 4),
        )
        for r in cur.fetchall():
            d = dict(r)
            hits.append(
                {
                    "source": "archive_fact",
                    "title": d.get("fact_type") or "fact",
                    "blurb": (d.get("fact_text") or "")[:400],
                }
            )
    except Exception:
        pass
    try:
        cur.execute(
            """
            SELECT subject, predicate, object
            FROM ops.memory_facts
            WHERE status = 'active'
              AND COALESCE(scope, 'business') <> 'personal'
              AND (
                subject ILIKE ANY(%s)
                OR COALESCE(object,'') ILIKE ANY(%s)
              )
            ORDER BY updated_at DESC NULLS LAST
            LIMIT %s
            """,
            (likes, likes, 4),
        )
        for r in cur.fetchall():
            d = dict(r)
            hits.append(
                {
                    "source": "memory",
                    "title": d.get("subject"),
                    "blurb": f"{d.get('predicate')}: {d.get('object')}"[:400],
                }
            )
    except Exception:
        pass
    return hits[: limit + 4]


def consult_archive_env(env: dict, query_text: str, *, limit: int = 6) -> list[dict]:
    try:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(
            host=env.get("POSTGRES_HOST", "127.0.0.1"),
            port=int(env.get("POSTGRES_PORT", "5432") or "5432"),
            user=env.get("POSTGRES_USER", "clawsum"),
            password=env.get("POSTGRES_PASSWORD", ""),
            dbname=env.get("POSTGRES_DB", "clawsum"),
        )
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        hits = consult_archive(cur, query_text, limit=limit)
        cur.close()
        conn.close()
        return hits
    except Exception as exc:
        print(f"WARN: archive consult connect: {exc}", flush=True)
        return []


# Boss codeword — standalone word, not "escalation.md" / "escalate to Gerald"
ESCALATE_RE = re.compile(r"(?i)(?:^|[^\w])escalate(?:[^\w]|$)")


def wants_escalate(text: str) -> bool:
    """True when Boss included the codeword 'escalate'."""
    return bool(ESCALATE_RE.search(text or ""))


def top_escalation_model(env: dict) -> str:
    """Highest-quality OpenRouter model (codeword escalate / frontier)."""
    return (
        (env.get("OPENROUTER_FRONTIER_MODEL") or "").strip()
        or (env.get("OPENROUTER_ESCALATION_MODEL") or "").strip()
        or (env.get("OPENROUTER_RESEARCH_MODEL") or "").strip()
        or "anthropic/claude-sonnet-4.6"
    )


def needs_deep_research(text: str, repos: list | None = None, archive_hits: list | None = None) -> bool:
    if wants_escalate(text or ""):
        return True
    if repos:
        return True
    blob = (text or "").lower()
    if any(c in blob for c in DEEP_CUES):
        return True
    if len(text or "") > 5000:
        return True
    if archive_hits and len(archive_hits) >= 3:
        return True
    return False


def _parse_json_content(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def chat_openrouter_json(env: dict, user_payload: Any, *, model: str) -> dict:
    try:
        import openrouter_client
    except Exception as exc:
        return {"error": f"openrouter_client: {exc}"}
    content = (
        user_payload if isinstance(user_payload, str) else json.dumps(user_payload)[:90000]
    )
    try:
        data = openrouter_client.chat(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": content},
            ],
            model=model,
            temperature=0.3,
            max_tokens=5000,
            response_format={"type": "json_object"},
            timeout=180,
        )
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        return _parse_json_content(text)
    except Exception as e:
        return {"error": str(e)}


def chat_json(
    env: dict,
    user_payload: Any,
    *,
    model: str | None = None,
    deep: bool = False,
    force_top: bool = False,
) -> dict:
    """GPT first; escalate to OpenRouter when deep, weak, or Boss said 'escalate'."""
    payload_text = (
        user_payload if isinstance(user_payload, str) else json.dumps(user_payload)
    )
    force_top = force_top or wants_escalate(payload_text)
    api_key = (env.get("OPENAI_API_KEY") or "").strip()
    model = model or env.get("GMAIL_DEEP_MODEL") or env.get("ANALYST_MODEL") or "gpt-4o-mini"
    raw: dict = {"error": "no provider"}
    if api_key and not deep and not force_top:
        body = {
            "model": model,
            "temperature": 0.35,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM},
                {
                    "role": "user",
                    "content": user_payload
                    if isinstance(user_payload, str)
                    else json.dumps(user_payload)[:90000],
                },
            ],
        }
        try:
            data = _http_json(
                "https://api.openai.com/v1/chat/completions",
                body,
                {"Authorization": f"Bearer {api_key}"},
                timeout=180,
            )
            raw = _parse_json_content(data["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                pass
            raw = {"error": f"HTTP {e.code}: {detail}"}
        except Exception as e:
            raw = {"error": str(e)}

    weak = bool(raw.get("error")) or (
        not (raw.get("vs_what_we_have") or raw.get("take") or raw.get("summary"))
    )
    should_escalate = deep or weak or force_top
    if should_escalate and (env.get("OPENROUTER_API_KEY") or "").strip():
        primary = top_escalation_model(env) if force_top else (
            env.get("OPENROUTER_RESEARCH_MODEL")
            or env.get("OPENROUTER_FRONTIER_MODEL")
            or env.get("OPENROUTER_ESCALATION_MODEL")
            or "google/gemini-2.5-pro"
        )
        print(
            f"analyst: {'codeword ' if force_top else ''}escalate → OpenRouter {primary}",
            flush=True,
        )
        esc = chat_openrouter_json(env, user_payload, model=primary)
        if not esc.get("error"):
            esc["_escalated"] = primary
            esc["_escalate_codeword"] = force_top
            return esc
        fallback = (
            env.get("OPENROUTER_RESEARCH_MODEL")
            if force_top
            else (env.get("OPENROUTER_ESCALATION_MODEL") or "anthropic/claude-sonnet-4.6")
        )
        if fallback and fallback != primary:
            print(f"analyst: escalate retry → {fallback}", flush=True)
            esc2 = chat_openrouter_json(env, user_payload, model=fallback)
            if not esc2.get("error"):
                esc2["_escalated"] = fallback
                esc2["_escalate_codeword"] = force_top
                return esc2
        if raw.get("error"):
            return esc
    return raw


def fetch_repo_readme(url_or_owner_repo: str) -> str:
    owner = repo = ""
    m = GITHUB_RE.search(url_or_owner_repo) or re.match(
        r"([^/]+)/([^/]+)$", url_or_owner_repo.strip()
    )
    if m:
        owner, repo = m.group(1), m.group(2).rstrip(".git")
    if not owner:
        return ""
    urls = [
        f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md",
        f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md",
        f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ClawsumAnalyst/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            if text and "<html" not in text[:80].lower():
                return f"REPO {owner}/{repo}\n{text[:6000]}"
        except Exception:
            continue
    return ""


def extract_repo_briefs(text: str, *, limit: int = 3) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for rx in (GITHUB_RE, GITLAB_RE):
        for m in rx.finditer(text or ""):
            key = f"{m.group(1)}/{m.group(2).rstrip('.git')}"
            if key in seen:
                continue
            seen.add(key)
            brief = fetch_repo_readme(m.group(0))
            if brief:
                found.append(brief)
            else:
                found.append(f"REPO {key} (readme not fetched — public link only)")
            if len(found) >= limit:
                return found
    return found


def _b64_image(data: bytes, content_type: str) -> str:
    ct = content_type if content_type in IMAGE_CT else "image/jpeg"
    return f"data:{ct};base64,{base64.b64encode(data).decode('ascii')}"


def analyze_image_bytes(
    env: dict,
    data: bytes,
    *,
    filename: str = "",
    content_type: str = "image/jpeg",
    context: str = "",
) -> dict:
    api_key = (env.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return {"error": "OPENAI_API_KEY missing"}
    if len(data) > 6_000_000:
        return {"error": "image too large", "skip": True}
    model = env.get("VISION_MODEL") or env.get("ANALYST_MODEL") or "gpt-4o-mini"
    prompt = (
        "Describe this image for Gerald's Clawsum archive. Plain English. "
        "What is it (screenshot, logo, mockup, diagram, photo, junk)? "
        "What text is readable? If it is a UI mockup or control-app layout, "
        "say whether Clawsum's cockpit/Inbox/Jarvis should adopt that look or flow. "
        "Filing label + adopt-or-not for design.\n"
        f"Filename: {filename}\nContext: {context[:400]}"
    )
    body = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 500,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": _b64_image(data, content_type)},
                    },
                ],
            }
        ],
    }
    try:
        data_out = _http_json(
            "https://api.openai.com/v1/chat/completions",
            body,
            {"Authorization": f"Bearer {api_key}"},
            timeout=90,
        )
        text = (data_out["choices"][0]["message"]["content"] or "").strip()
        return {
            "summary": text,
            "filename": filename,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "filename": filename}


def load_image_bytes(att: dict, env: dict) -> tuple[bytes, str] | None:
    uri = att.get("uri") or ""
    ct = (att.get("content_type") or att.get("contentType") or "").lower()
    kind = (att.get("kind") or "").lower()
    name = (att.get("filename") or "").lower()
    is_img = (
        kind in IMAGE_KINDS
        or ct.startswith("image/")
        or name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
    )
    if not is_img or not uri:
        return None
    try:
        import minio_store

        raw, meta = minio_store.download_uri_bytes(uri, env)
        return raw, meta.get("content_type") or ct or "image/jpeg"
    except Exception as exc:
        print(f"WARN: image fetch failed {att.get('filename')}: {exc}", flush=True)
        return None


def analyze_attachments(
    env: dict,
    attachments: list[dict],
    *,
    context: str = "",
    limit: int = 4,
) -> list[dict]:
    notes: list[dict] = []
    for att in attachments or []:
        if len(notes) >= limit:
            break
        loaded = load_image_bytes(att, env)
        if not loaded:
            continue
        raw, ct = loaded
        result = analyze_image_bytes(
            env,
            raw,
            filename=att.get("filename") or "",
            content_type=ct,
            context=context,
        )
        result["media_id"] = att.get("media_id") or att.get("id")
        result["uri"] = att.get("uri")
        notes.append(result)
    return notes


def persist_image_analysis(cur, notes: list[dict]) -> int:
    n = 0
    for note in notes:
        mid = note.get("media_id")
        if not mid or note.get("error"):
            continue
        payload = {
            "analysis": {
                "summary": note.get("summary"),
                "filename": note.get("filename"),
                "analyzed_at": note.get("analyzed_at"),
                "style": "chatgpt",
            }
        }
        try:
            cur.execute(
                """
                UPDATE ops.media_objects
                SET meta = COALESCE(meta, '{}'::jsonb) || %s::jsonb,
                    updated_at = now()
                WHERE id = %s::uuid
                """,
                (json.dumps(payload), str(mid)),
            )
            n += 1
        except Exception as exc:
            print(f"WARN: persist image analysis {mid}: {exc}", flush=True)
    return n


def analyze_pending_images(cur, env: dict, *, limit: int = 8) -> int:
    try:
        cur.execute(
            """
            SELECT id::text, filename, content_type, uri, kind, source_ref
            FROM ops.media_objects
            WHERE kind = 'photo'
              AND (meta->'analysis' IS NULL OR meta->'analysis' = 'null'::jsonb)
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = [dict(r) for r in cur.fetchall()]
    except Exception as exc:
        print(f"WARN: pending image query: {exc}", flush=True)
        return 0
    notes = analyze_attachments(env, rows, context="archived attachment", limit=limit)
    return persist_image_analysis(cur, notes)


def normalize_analysis(raw: dict, *, fallback_subject: str = "") -> dict:
    if raw.get("error"):
        return raw
    priority = (raw.get("priority") or "medium").lower()
    if priority not in ("urgent", "high", "medium", "low", "noise"):
        priority = "medium"
    status = (raw.get("review_status") or "").lower()
    skip = bool(raw.get("skip")) or priority == "noise"
    if status not in ("needs_boss", "reviewed", "ignored"):
        status = "ignored" if skip else ("needs_boss" if raw.get("action_required") else "reviewed")
    if skip:
        status = "ignored"
        priority = "noise" if priority == "noise" else "low"
    suggestions = raw.get("suggestions") or []
    if isinstance(suggestions, str):
        suggestions = [suggestions]
    questions = raw.get("questions_for_boss") or []
    if isinstance(questions, str):
        questions = [questions]
    report = (raw.get("report_markdown") or "").strip()
    if not report:
        bits = [
            f"## {fallback_subject or 'Note'}",
            "",
            raw.get("summary") or "",
            "",
            "**My take:** " + (raw.get("take") or ""),
            "",
            "**Does this apply?** " + (raw.get("project_fit") or ""),
            "",
            "**Compared to what we have:** " + (raw.get("vs_what_we_have") or ""),
        ]
        if suggestions:
            bits += ["", "### What I'd do"] + [f"- {s}" for s in suggestions]
        report = "\n".join(bits)
    summary = (raw.get("summary") or raw.get("take") or "")[:4000]
    take = (raw.get("take") or summary)[:2000]
    recommendation = "; ".join(str(s) for s in suggestions[:5])[:4000]
    if skip and not recommendation:
        recommendation = "Ignore — not worth your time."
    slugs = {
        "clawsum-platform",
        "personal-admin",
        "wnn-client",
        "vocalitic",
        "roofing-os",
        "real-estate",
        "techtasia",
        "acceptai-fastbuy",
        "hardware-local-ai",
        "media-production",
    }
    project_slug = (raw.get("project_slug") or "").strip()
    if project_slug not in slugs:
        project_slug = "clawsum-platform" if not skip else "personal-admin"
    owner = (raw.get("owner_agent") or "Clawsum Admin").strip()
    verdict = (raw.get("adopt_verdict") or "").strip()
    if verdict not in ("adopt", "side_by_side", "steal_ideas", "skip_noise"):
        verdict = "skip_noise" if skip else "steal_ideas"
    skills = raw.get("skills_needed") or []
    if isinstance(skills, str):
        skills = [skills]
    return {
        "summary": summary,
        "intent": take,
        "take": take,
        "recommendation": recommendation,
        "priority": "low" if priority == "noise" else priority,
        "review_status": status,
        "action_required": bool(raw.get("action_required")) and not skip,
        "is_noise": skip,
        "questions": [str(q)[:240] for q in questions[:8]],
        "suggestions": [str(s) for s in suggestions[:8]],
        "project_fit": raw.get("project_fit") or "",
        "business_slug": project_slug,
        "owner_agent": owner,
        "adopt_verdict": verdict,
        "mockup_adopt": raw.get("mockup_adopt") or "",
        "skills_needed": [str(s) for s in skills[:8]],
        "vs_what_we_have": raw.get("vs_what_we_have") or "",
        "image_notes": raw.get("image_notes") or "",
        "repo_notes": raw.get("repo_notes") or "",
        "report_markdown": report,
        "signals": ["chatgpt_analyst", f"owner:{owner}", f"adopt:{verdict}"],
        "analysis_json": {
            "style": "chatgpt",
            "take": take,
            "value_assessment": raw.get("take") or raw.get("project_fit"),
            "project_fit": raw.get("project_fit"),
            "project_slug": project_slug,
            "owner_agent": owner,
            "adopt_verdict": verdict,
            "mockup_adopt": raw.get("mockup_adopt"),
            "skills_needed": skills[:8],
            "vs_what_we_have": raw.get("vs_what_we_have"),
            "suggested_actions": suggestions[:8],
            "image_notes": raw.get("image_notes"),
            "repo_notes": raw.get("repo_notes"),
            "skip": skip,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def analyze_email(env: dict, email: dict, *, cur=None) -> dict:
    body = email.get("body_text") or email.get("snippet") or ""
    attachments = email.get("attachments") or []
    if isinstance(attachments, str):
        try:
            attachments = json.loads(attachments)
        except Exception:
            attachments = []
    image_notes = analyze_attachments(
        env,
        attachments,
        context=f"Email: {email.get('subject') or ''} from {email.get('from_addr') or ''}",
        limit=int(env.get("ANALYST_IMAGE_LIMIT", "3") or 3),
    )
    if cur is not None:
        persist_image_analysis(cur, image_notes)
    blob = f"{email.get('subject') or ''}\n{body}"
    repos = extract_repo_briefs(blob)
    archive = consult_archive(cur, blob)
    payload = {
        "kind": "email",
        "from": email.get("from_addr"),
        "subject": email.get("subject"),
        "received_at": str(email.get("received_at") or ""),
        "body": (body or "")[:24000],
        "attachment_names": [a.get("filename") for a in attachments if isinstance(a, dict)],
        "image_analyses": [
            {k: n.get(k) for k in ("filename", "summary", "error")} for n in image_notes
        ],
        "repo_readmes": repos,
        "chatgpt_archive_hits": archive,
        "enterprise": enterprise_snapshot(cur),
        "instruction": (
            "Consult chatgpt_archive_hits — Gerald may have already decided this. "
            "If unclear, ask leading improvement questions."
        ),
    }
    deep = needs_deep_research(blob, repos, archive)
    raw = chat_json(env, payload, deep=deep, force_top=wants_escalate(blob))
    out = normalize_analysis(raw, fallback_subject=email.get("subject") or "Email")
    if not out.get("error"):
        out["analysis_json"]["archive_hits"] = archive[:6]
        out["analysis_json"]["escalated_model"] = raw.get("_escalated")
        out["analysis_json"]["deep_research"] = deep
    if image_notes and not out.get("error"):
        out["analysis_json"]["images"] = [
            {k: n.get(k) for k in ("filename", "summary", "media_id", "uri", "error")}
            for n in image_notes
        ]
    return out


def analyze_task(env: dict, task: dict, *, cur=None) -> dict:
    blob = f"{task.get('title') or ''}\n{task.get('description') or ''}"
    repos = extract_repo_briefs(blob)
    archive = consult_archive(cur, blob)
    payload = {
        "kind": "task",
        "title": task.get("title"),
        "description": (task.get("description") or "")[:12000],
        "status": task.get("status"),
        "repo_readmes": repos,
        "chatgpt_archive_hits": archive,
        "enterprise": enterprise_snapshot(cur),
        "ask": (
            "Treat this like he pasted a to-do into ChatGPT. "
            "Use chatgpt_archive_hits if he already scoped this. "
            "Say what it really is, whether it is worth doing, who should own it, "
            "and the first move. Ask leading questions if the outcome is fuzzy."
        ),
    }
    deep = needs_deep_research(blob, repos, archive)
    raw = chat_json(
        env,
        payload,
        model=env.get("TASK_ANALYZE_MODEL") or env.get("ANALYST_MODEL"),
        deep=deep,
        force_top=wants_escalate(blob),
    )
    out = normalize_analysis(raw, fallback_subject=task.get("title") or "Task")
    if not out.get("error"):
        out["analysis_json"]["archive_hits"] = archive[:6]
        out["analysis_json"]["escalated_model"] = raw.get("_escalated")
        out["analysis_json"]["deep_research"] = deep
    return out
