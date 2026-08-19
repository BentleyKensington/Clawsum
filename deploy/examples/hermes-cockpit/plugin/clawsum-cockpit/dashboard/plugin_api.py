"""
Clawsum cockpit backend — FastAPI router for Clawsum dashboard plugin.

Mounted at: /api/plugins/clawsum-cockpit/

Env (optional, set on VPS / Paperclip container):
  CLAWSUM_BOSS_URL=https://boss.example.com
  CLAWSUM_OPENCLAW_URL=https://clawsum.example.com
  CLAWSUM_GRAFANA_URL=https://grafana.example.com
  CLAWSUM_GRAFANA_EMBED_URL=https://grafana.example.com/d/clawsum-health?...&kiosk
  PAPERCLIP_API=http://127.0.0.1:3100/api
  PAPERCLIP_COMPANY_ID=...
  DATABASE_URL or POSTGRES_* for ops.approvals / ops.conversations
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response

router = APIRouter()


def _hermes_home() -> Path:
    return Path(_env("HERMES_HOME", "/paperclip/.hermes"))


def _session_briefs_dir() -> Path:
    d = _hermes_home() / "session-briefs"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return d


def _pg_connect():
    import psycopg2

    return psycopg2.connect(
        host=_env("POSTGRES_HOST", "127.0.0.1"),
        port=int(_env("POSTGRES_PORT", "5432") or "5432"),
        user=_env("POSTGRES_USER", "clawsum"),
        password=_env("POSTGRES_PASSWORD", ""),
        dbname=_env("POSTGRES_DB", "clawsum"),
    )


def _list_session_brief_files(limit: int = 50) -> list[dict[str, Any]]:
    """Markdown files under HERMES_HOME/session-briefs/ (durable file archive)."""
    root = _session_briefs_dir()
    if not root.is_dir():
        return []
    items: list[dict[str, Any]] = []
    paths = sorted(root.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in paths[:limit]:
        try:
            body = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        greeting = ""
        for line in body.splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                greeting = s[:200]
                break
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        items.append(
            {
                "id": p.stem,
                "created_at": mtime.isoformat(),
                "greeting": greeting,
                "body_md": body,
                "source": "file",
                "file_uri": str(p),
                "filename": p.name,
            }
        )
    return items


def _list_session_briefs_db(limit: int = 50) -> list[dict[str, Any]] | None:
    try:
        import psycopg2.extras  # type: ignore

        conn = _pg_connect()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id::text, created_at, session_key, greeting, body_md,
                           source, file_uri
                    FROM ops.session_briefs
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        for r in rows:
            if r.get("created_at") is not None:
                r["created_at"] = r["created_at"].isoformat()
        return rows
    except Exception:
        return None


def _save_session_brief(
    body_md: str,
    *,
    greeting: str = "",
    session_key: str = "",
    source: str = "hermes",
) -> dict[str, Any]:
    body_md = (body_md or "").strip()
    if not body_md:
        raise ValueError("body_md required")
    if not greeting:
        for line in body_md.splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                greeting = s[:200]
                break
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d-%H%M%S")
    safe_key = re.sub(r"[^a-zA-Z0-9_-]+", "-", (session_key or "").strip())[:40].strip("-")
    filename = f"{stamp}{('-' + safe_key) if safe_key else ''}.md"
    path = _session_briefs_dir() / filename
    header = f"# Session Startup Brief — {now.isoformat()}\n\n"
    if not body_md.lstrip().startswith("#"):
        text = header + body_md + "\n"
    else:
        text = body_md if body_md.endswith("\n") else body_md + "\n"
    try:
        path.write_text(text, encoding="utf-8")
        file_uri = str(path)
    except OSError as exc:
        file_uri = ""
        # Still try DB even if file write fails
        if not body_md:
            raise exc

    row: dict[str, Any] = {
        "created_at": now.isoformat(),
        "session_key": session_key or None,
        "greeting": greeting or None,
        "body_md": text,
        "source": source if source in ("hermes", "manual", "import") else "hermes",
        "file_uri": file_uri or None,
        "filename": filename,
    }
    try:
        import psycopg2.extras  # type: ignore

        conn = _pg_connect()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO ops.session_briefs
                      (session_key, greeting, body_md, source, file_uri)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id::text, created_at, session_key, greeting, body_md,
                              source, file_uri
                    """,
                    (
                        row["session_key"],
                        row["greeting"],
                        row["body_md"],
                        row["source"],
                        row["file_uri"],
                    ),
                )
                db_row = dict(cur.fetchone())
        conn.close()
        if db_row.get("created_at") is not None:
            db_row["created_at"] = db_row["created_at"].isoformat()
        db_row["filename"] = filename
        return db_row
    except Exception:
        if not file_uri:
            raise
        row["id"] = path.stem
        row["db"] = False
        return row


def _assets_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent / "assets",
        Path(__file__).resolve().parents[1] / "assets",
        Path("/paperclip/.hermes/clawsum-assets"),
        Path("/docker/clawsum/deploy/examples/hermes-cockpit/assets"),
        Path("/docker/clawsum/examples/hermes-cockpit/assets"),
    ]
    for p in candidates:
        if p.is_dir():
            return p
    return candidates[0]


_RUNTIME_ENV_CACHE: dict[str, str] | None = None


def _load_runtime_env() -> dict[str, str]:
    """Load POSTGRES_* etc. for Hermes plugin process (Paperclip often lacks them)."""
    global _RUNTIME_ENV_CACHE
    if _RUNTIME_ENV_CACHE is not None:
        return _RUNTIME_ENV_CACHE
    out: dict[str, str] = {}
    candidates = [
        Path(__file__).resolve().parent / "clawsum-runtime.env",
        Path("/paperclip/.hermes/clawsum-runtime.env"),
        Path("/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/clawsum-runtime.env"),
        Path("/docker/clawsum/.env"),
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                if not k:
                    continue
                out.setdefault(k, v.strip().strip('"').strip("'"))
        except OSError:
            continue
    _RUNTIME_ENV_CACHE = out
    return out


def _env(key: str, default: str = "") -> str:
    v = (os.environ.get(key) or "").strip()
    if v:
        return v
    return (_load_runtime_env().get(key) or default).strip()


def _http_json(url: str, timeout: float = 4.0) -> Any | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "plugin": "clawsum-cockpit"}


def _authority_paths() -> list[Path]:
    here = Path(__file__).resolve().parent
    return [
        here / "authority.json",
        Path("/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/authority.json"),
        Path("/docker/clawsum/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/authority.json"),
        Path("/docker/clawsum/deploy/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/authority.json"),
    ]


def _load_authority() -> dict[str, Any]:
    for p in _authority_paths():
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("agents") and data.get("skills"):
                    data["ok"] = True
                    data["path"] = str(p)
                    return data
            except Exception:
                continue
    return {
        "ok": False,
        "agents": [],
        "skills": [],
        "tiers": {},
        "error": "authority.json missing — re-run install-hermes-cockpit.sh",
    }


@router.get("/authority")
def authority() -> JSONResponse:
    """Agents + skills auth matrix for cockpit left nav."""
    data = _load_authority()
    agents = data.get("agents") or []
    skills = data.get("skills") or []
    # Derive agent → skills for UI
    by_agent: dict[str, list[str]] = {}
    for sk in skills:
        if not isinstance(sk, dict):
            continue
        sid = sk.get("id") or ""
        for aid in sk.get("agents") or []:
            by_agent.setdefault(str(aid), []).append(str(sid))
    for ag in agents:
        if isinstance(ag, dict):
            aid = str(ag.get("id") or "")
            ag["skills"] = sorted(by_agent.get(aid, []))
    data["agents"] = agents
    data["skill_count"] = len(skills)
    data["agent_count"] = len(agents)
    data["project_count"] = len(data.get("projects") or [])
    return JSONResponse(data)


_SKILL_BLURBS: dict[str, str] = {
    "ceo-daily-brief": "Builds the morning ops brief from Paperclip + inbox signals. Read-only; posts only when asked.",
    "hermes-proactive-drive": "Session startup brief + every-reply Next guidance.",
    "overwatch-approvals": "Surfaces Tier-gated waits and approval queue health across cells.",
    "paperclip-task-routing": "Creates/updates Paperclip tasks from briefs and Ask Boss items.",
    "resume-policy-gate": "Blocks risky resume/auto-continue unless policy allows.",
    "gmail-inbox-review": "Per-email analysis for clawsums@ — needs_boss, drafts, reminders.",
    "gmail-sync-triage": "Sync + coarse triage into Postgres / Paperclip.",
    "people-places-crm": "People/places CRM lookups across cells.",
    "reminders-boss-nudge": "Scheduled Boss nudges (Telegram when wired).",
    "chatgpt-archive": "Search prior ChatGPT/archive conversations for context.",
    "cell-isolation-check": "Ensures cell boundaries — no cross-tenant credential bleed.",
    "ghl-lead-ops": "GHL lead pipeline ops for WNN.",
    "ghl-reengage": "Re-engage dormant GHL contacts (draft-first).",
    "vocalitic-health": "Vocalitic / local AI health checks.",
    "roofing-storm-intel": "Storm/roofing intel research — advisory, not claims.",
    "real-estate-pipeline": "RE deal pipeline notes and ArcadeDB hooks.",
    "commerce-fastbuy": "AcceptAI / FastBuy commerce lane drafts.",
    "techtasia-planning": "Techtasia priorities and planning board.",
    "personal-admin": "Gerald personal-admin lane (mail, calendar hygiene).",
    "hardware-local-ai": "Local hardware / AI box status.",
    "research-brief": "Competitive / market research briefs with citations.",
    "credential-hygiene": "Credential inventory and rotation reminders.",
    "draft-comms-approval-gated": "Outbound drafts only — send requires Boss.",
    "telegram-ops-notify": "Ops alerts to Telegram when configured.",
    "clawsum-com-funnel": "Marketing funnel / clawsum.com site deploy hygiene.",
    "audit-log-review": "Read ops.audit_logs for Boss review.",
    "openclaw-agent-config": "OpenClaw agent/gateway config changes (Tier-gated).",
    "minio-archive-store": "MinIO archive / attachment store ops.",
    "postgres-ops-schema": "Ops schema migrations and reports.",
    "data-scraper": "In-house scraper — Data tool, not its own agent.",
    "data-osint": "OSINT + global monitoring; extract public details.",
    "data-chat-extract": "Pull durable facts from chat/archive into memory.",
    "graphify-obsidian": "Graphify / 3D Obsidian memory visualizer.",
    "agent-daily-review": "Each agent reviews memory/tasks; feeds morning brief.",
    "hermes-daily-alert": "Hermes daily sweep — money, leverage, must-know.",
    "legal-review": "Contract/terms review. File/sign = Tier 3.",
    "content-repurpose": "Longform → clips, threads, posts.",
    "ppc-ads-ops": "PPC campaigns. Spend = Tier 2.",
    "bookkeeper-ledger": "Invoices, receipts, books. Pay/wire = Tier 3.",
    "seo-aeo-geo": "GSC, GMB, knowledge panel, AEO/GEO.",
    "funnel-builder": "Offers, landing pages, CRO.",
    "calendar-ops": "Holds and scheduling. Invite send = Tier 2.",
    "social-posting": "Schedule posts and reply to comments.",
    "llm-compare": "Bake-off models; write scorecard.",
    "cockpit-hud": "CEO cockpit HUD — gauges, marquee, live tiles.",
    "inbound-adopt-evaluate": "Evaluate inbound tools/mockups for adopt.",
    "skill-forge": "Turn adopt/steal into a SKILL.md.",
    "discord-hq": "Discord HQ notify/bindings.",
    "ghl-weekly-rei-report": "Weekly REI GHL report.",
    "pentest-threat-model": "Living threat register.",
    "pentest-surface-scan": "Read-only surface scan.",
    "pentest-report": "Security reports.",
    "pentest-notify": "High/Critical notify.",
}


def _paperclip_issue_list(limit: int = 40) -> tuple[list[dict[str, Any]], str | None]:
    """Fetch open Paperclip issues with titles for the Catalog page."""
    api = _env("PAPERCLIP_API", "http://127.0.0.1:3100/api").rstrip("/")
    company = _env("PAPERCLIP_COMPANY_ID")
    if not company:
        return [], "PAPERCLIP_COMPANY_ID not set"
    out: list[dict[str, Any]] = []
    err: str | None = None
    for status in ("todo", "in_progress", "blocked", "backlog"):
        raw = _http_json(f"{api}/companies/{company}/issues?status={status}")
        if raw is None:
            err = err or f"Paperclip issues unreachable ({status})"
            continue
        items = raw if isinstance(raw, list) else (raw.get("issues") or raw.get("items") or [])
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            title = (
                it.get("title")
                or it.get("name")
                or it.get("summary")
                or it.get("identifier")
                or it.get("id")
                or "Untitled"
            )
            desc = (
                it.get("description")
                or it.get("body")
                or it.get("blurb")
                or it.get("summary")
                or ""
            )
            if isinstance(desc, str) and len(desc) > 280:
                desc = desc[:277] + "…"
            out.append(
                {
                    "id": str(it.get("id") or it.get("identifier") or title),
                    "identifier": it.get("identifier") or it.get("key") or "",
                    "title": str(title),
                    "status": status,
                    "blurb": str(desc).strip()
                    or f"Paperclip issue in {status.replace('_', ' ')} — open in Paperclip for full detail.",
                    "assignee": it.get("assignee")
                    or it.get("assigneeName")
                    or it.get("agent")
                    or "",
                    "href": _env("PAPERCLIP_PUBLIC_URL", "https://paperclip.clawsum.com"),
                }
            )
            if len(out) >= limit:
                return out, err
    if not out and err:
        return [], err
    if not out:
        return [], "No open Paperclip issues in todo/in_progress/blocked/backlog (or not enough data)."
    return out, err


@router.get("/catalog")
def catalog() -> JSONResponse:
    """Explained catalog: agents, skills, projects (cells), tasks."""
    data = _load_authority()
    agents = []
    for ag in data.get("agents") or []:
        if not isinstance(ag, dict):
            continue
        agents.append(
            {
                "id": ag.get("id"),
                "name": ag.get("name") or ag.get("id"),
                "cells": ag.get("cells") or [],
                "domains": ag.get("domains") or "",
                "blurb": ag.get("blurb")
                or ag.get("domains")
                or "Specialist agent in the Clawsum org chart.",
                "skills": ag.get("skills") or [],
            }
        )
    # attach skills lists
    by_agent: dict[str, list[str]] = {}
    skills_out = []
    for sk in data.get("skills") or []:
        if not isinstance(sk, dict):
            continue
        sid = str(sk.get("id") or "")
        for aid in sk.get("agents") or []:
            by_agent.setdefault(str(aid), []).append(sid)
        skills_out.append(
            {
                "id": sid,
                "tier": sk.get("tier"),
                "agents": sk.get("agents") or [],
                "cells": sk.get("cells") or [],
                "credentials": sk.get("credentials") or [],
                "blurb": sk.get("blurb")
                or _SKILL_BLURBS.get(sid)
                or "Skill in the authority matrix. Tier gates what can run without Boss approval.",
                "primary": sid in (data.get("primary_skills") or []),
            }
        )
    for ag in agents:
        aid = str(ag.get("id") or "")
        ag["skills"] = sorted(by_agent.get(aid, []))

    projects = []
    for pr in data.get("projects") or []:
        if isinstance(pr, dict):
            projects.append(pr)

    # Merge live business cells from Postgres when available
    try:
        import psycopg2  # type: ignore

        conn = psycopg2.connect(
            host=_env("POSTGRES_HOST", "127.0.0.1"),
            port=int(_env("POSTGRES_PORT", "5432") or "5432"),
            user=_env("POSTGRES_USER", "clawsum"),
            password=_env("POSTGRES_PASSWORD", ""),
            dbname=_env("POSTGRES_DB", "clawsum"),
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT slug, name, COALESCE(notes, '') FROM ops.businesses WHERE active ORDER BY slug"
                )
                known = {str(p.get("id")) for p in projects}
                for slug, name, notes in cur.fetchall():
                    sid = str(slug)
                    if sid in known:
                        continue
                    projects.append(
                        {
                            "id": sid,
                            "name": name or sid,
                            "kind": "cell",
                            "blurb": (notes or "").strip()
                            or f"Active business cell `{sid}` — explanation not yet documented.",
                        }
                    )
        conn.close()
    except Exception:
        pass

    tasks, task_err = _paperclip_issue_list()
    notes = []
    if not agents:
        notes.append("Agents: not enough data — authority.json missing or empty.")
    if not skills_out:
        notes.append("Skills: not enough data — authority.json missing or empty.")
    if not projects:
        notes.append("Projects: not enough data — no cells documented and DB unreachable.")
    if task_err:
        notes.append(f"Tasks: {task_err}")

    return JSONResponse(
        {
            "ok": True,
            "agents": agents,
            "skills": skills_out,
            "projects": projects,
            "tasks": tasks,
            "tiers": data.get("tiers") or {},
            "notes": notes,
            "links": links(),
        }
    )


def _metric_label(value: Any) -> str:
    """Escape a Prometheus label value."""
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


@router.get("/metrics", response_class=PlainTextResponse)
def metrics() -> PlainTextResponse:
    """Low-cardinality CEO/ops metrics for the local Prometheus instance."""
    lines = [
        "# HELP clawsum_cockpit_up Clawsum cockpit metrics endpoint is serving.",
        "# TYPE clawsum_cockpit_up gauge",
        "clawsum_cockpit_up 1",
    ]

    authority_data = _load_authority()
    lines.extend(
        [
            "# HELP clawsum_authority_agents Number of core authority agents.",
            "# TYPE clawsum_authority_agents gauge",
            f"clawsum_authority_agents {len(authority_data.get('agents') or [])}",
            "# HELP clawsum_authority_skills Number of governed skills.",
            "# TYPE clawsum_authority_skills gauge",
            f"clawsum_authority_skills {len(authority_data.get('skills') or [])}",
        ]
    )

    conn = None
    try:
        import psycopg2  # type: ignore

        conn = psycopg2.connect(
            host=_env("POSTGRES_HOST", "127.0.0.1"),
            port=int(_env("POSTGRES_PORT", "5432") or "5432"),
            user=_env("POSTGRES_USER", "clawsum"),
            password=_env("POSTGRES_PASSWORD", ""),
            dbname=_env("POSTGRES_DB", "clawsum"),
        )
        conn.autocommit = True

        def rows(sql: str) -> list[tuple[Any, ...]]:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    return list(cur.fetchall())
            except Exception:
                return []

        lines.extend(
            [
                "# HELP clawsum_postgres_up Cockpit connection to the ops database.",
                "# TYPE clawsum_postgres_up gauge",
                "clawsum_postgres_up 1",
            ]
        )

        for status, count in rows(
            "SELECT processing_status, count(*) FROM ops.emails GROUP BY 1"
        ):
            lines.append(
                f'clawsum_emails{{processing_status="{_metric_label(status)}"}} {int(count)}'
            )
        for status, count in rows(
            "SELECT COALESCE(review_status, 'unreviewed'), count(*) "
            "FROM ops.emails GROUP BY 1"
        ):
            lines.append(
                f'clawsum_email_reviews{{review_status="{_metric_label(status)}"}} {int(count)}'
            )

        sync_rows = rows(
            "SELECT COALESCE(EXTRACT(EPOCH FROM (now() - last_sync_at)), -1), "
            "messages_total FROM ops.email_sync_state WHERE id = 1"
        )
        if sync_rows:
            age, total = sync_rows[0]
            lines.append(f"clawsum_gmail_sync_age_seconds {float(age):.3f}")
            lines.append(f"clawsum_gmail_messages_total {int(total)}")

        for status, count in rows(
            "SELECT status, count(*) FROM ops.approvals GROUP BY 1"
        ):
            lines.append(
                f'clawsum_approvals{{status="{_metric_label(status)}"}} {int(count)}'
            )
        business_rows = rows("SELECT count(*) FROM ops.businesses WHERE active")
        if business_rows:
            lines.append(f"clawsum_business_cells_active {int(business_rows[0][0])}")
        audit_rows = rows(
            "SELECT count(*) FROM ops.audit_logs "
            "WHERE created_at >= now() - interval '24 hours'"
        )
        if audit_rows:
            lines.append(f"clawsum_audit_events_24h {int(audit_rows[0][0])}")
    except Exception:
        lines.extend(
            [
                "# HELP clawsum_postgres_up Cockpit connection to the ops database.",
                "# TYPE clawsum_postgres_up gauge",
                "clawsum_postgres_up 0",
            ]
        )
    finally:
        if conn is not None:
            conn.close()

    api = _env("PAPERCLIP_API", "http://127.0.0.1:3100/api").rstrip("/")
    company = _env("PAPERCLIP_COMPANY_ID")
    paperclip_up = 1 if _http_json(f"{api}/health") is not None else 0
    lines.extend(
        [
            "# HELP clawsum_paperclip_api_up Paperclip API responds to cockpit.",
            "# TYPE clawsum_paperclip_api_up gauge",
            f"clawsum_paperclip_api_up {paperclip_up}",
        ]
    )
    if company:
        for status in ("backlog", "todo", "in_progress", "blocked", "done"):
            issues = _http_json(f"{api}/companies/{company}/issues?status={status}")
            if isinstance(issues, list):
                lines.append(
                    f'clawsum_paperclip_issues{{status="{status}"}} {len(issues)}'
                )

    return PlainTextResponse(
        "\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/links")
def links() -> dict[str, str]:
    paperclip = _env(
        "CLAWSUM_BOSS_URL",
        _env("PAPERCLIP_PUBLIC_URL", "https://paperclip.clawsum.com"),
    )
    openclaw = _env("CLAWSUM_OPENCLAW_URL", "https://openclaw.clawsum.com")
    grafana = _env("CLAWSUM_GRAFANA_URL", "https://grafana.clawsum.com")
    return {
        "boss": paperclip,
        "paperclip": paperclip,
        "openclaw": openclaw,
        "openclaw_ui": openclaw,
        "grafana": grafana,
        "grafana_embed": _env(
            "CLAWSUM_GRAFANA_EMBED_URL",
            "https://grafana.clawsum.com/d/clawsum-operations?orgId=1&kiosk",
        ),
        "grafana_ops": _env(
            "CLAWSUM_GRAFANA_OPS_URL",
            "https://grafana.clawsum.com/d/clawsum-operations?orgId=1&kiosk",
        ),
        "grafana_health": _env(
            "CLAWSUM_GRAFANA_HEALTH_URL",
            "https://grafana.clawsum.com/d/clawsum-health?orgId=1&kiosk",
        ),
        "connect": _env("CLAWSUM_CONNECT_URL", "https://connect.clawsum.com"),
        "login": _env("CLAWSUM_LOGIN_URL", "https://login.clawsum.com"),
        "hermes": _env("CLAWSUM_HERMES_URL", "https://boss.clawsum.com"),
        "arcade": _env("CLAWSUM_ARCADE_URL", "https://arcade.clawsum.com"),
    }


@router.get("/brief")
def brief() -> JSONResponse:
    """CEO daily brief payload — Paperclip + approvals when available."""
    api = _env("PAPERCLIP_API", "http://127.0.0.1:3100/api").rstrip("/")
    company = _env("PAPERCLIP_COMPANY_ID")
    paperclip_note = ""
    if not company:
        companies = _http_json(f"{api}/companies")
        if isinstance(companies, list) and companies:
            claw = next(
                (
                    c
                    for c in companies
                    if isinstance(c, dict)
                    and str(c.get("name") or "").lower() == "clawsum"
                ),
                None,
            )
            pick = claw if isinstance(claw, dict) else companies[0]
            if isinstance(pick, dict) and pick.get("id"):
                company = str(pick["id"])
                paperclip_note = f"auto company {pick.get('name') or company}"
    tasks: dict[str, Any] = {}
    paperclip_error = ""
    if company:
        dash = _http_json(f"{api}/companies/{company}/dashboard")
        if isinstance(dash, dict):
            tasks = {
                "agents": dash.get("agents") or dash.get("agentCounts"),
                "issues": dash.get("tasks") or dash.get("issueCounts") or dash.get("issues"),
                "company_id": company,
            }
            # Flatten useful counts into priorities later
            if not any(tasks.get(k) for k in ("agents", "issues")):
                # Keep raw-ish snapshot so UI isn't empty when schema differs
                for k in ("openIssueCount", "todoCount", "inProgressCount", "blockedCount"):
                    if dash.get(k) is not None:
                        tasks[k] = dash.get(k)
        else:
            paperclip_error = f"dashboard fetch failed for {company}"
    else:
        paperclip_error = "PAPERCLIP_COMPANY_ID unset and /companies empty or unreachable"

    approvals_pending = 0
    businesses = 0
    archive_pending = 0
    try:
        import psycopg2  # type: ignore

        conn = psycopg2.connect(
            host=_env("POSTGRES_HOST", "127.0.0.1"),
            port=int(_env("POSTGRES_PORT", "5432") or "5432"),
            user=_env("POSTGRES_USER", "clawsum"),
            password=_env("POSTGRES_PASSWORD", ""),
            dbname=_env("POSTGRES_DB", "clawsum"),
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM ops.approvals WHERE status = 'pending'"
                )
                approvals_pending = int(cur.fetchone()[0])
                cur.execute("SELECT count(*) FROM ops.businesses WHERE active")
                businesses = int(cur.fetchone()[0])
                try:
                    cur.execute(
                        """
                        SELECT count(*) FROM ops.conversations
                        WHERE scope IN ('business', 'mixed', 'unknown')
                          AND work_status IN ('pending', 'blocked')
                        """
                    )
                    archive_pending = int(cur.fetchone()[0])
                except Exception:
                    archive_pending = 0
        conn.close()
    except Exception as exc:
        return JSONResponse(
            {
                "ok": True,
                "source": "partial",
                "warning": f"overwatch db unavailable: {exc}",
                "priorities": [
                    "Open Boss UI and complete CLA-41 clarifications before enabling heartbeats.",
                    "Confirm daily report cron uses CRON_TZ=America/Chicago (7am local).",
                ],
                "pending_approvals": approvals_pending,
                "business_cells": businesses,
                "archive_pending": archive_pending,
                "jarvis": _jarvis_kpi(),
                "paperclip": tasks,
                "paperclip_error": paperclip_error or None,
                "links": links(),
            }
        )

    priorities = []
    if approvals_pending:
        priorities.append(f"{approvals_pending} approval(s) waiting in overwatch queue.")
    if paperclip_error and not tasks:
        priorities.append(f"Paperclip: {paperclip_error}")
    elif not tasks:
        priorities.append("Paperclip dashboard returned no task counts (check API shape).")
    else:
        issues = tasks.get("issues") or {}
        if isinstance(issues, dict):
            for label, key in (
                ("open", "open"),
                ("in progress", "inProgress"),
                ("in progress", "in_progress"),
                ("blocked", "blocked"),
                ("todo", "todo"),
                ("backlog", "backlog"),
                ("done", "done"),
            ):
                n = issues.get(key)
                if n in (None, 0, "0"):
                    n = issues.get(label)
                if n not in (None, 0, "0"):
                    line = f"Paperclip {label}: {n}"
                    if line not in priorities:
                        priorities.append(line)
        agents = tasks.get("agents")
        if isinstance(agents, dict) and agents:
            priorities.append(
                "Agents: "
                + ", ".join(f"{k}={v}" for k, v in list(agents.items())[:6])
            )
        for k in ("openIssueCount", "todoCount", "inProgressCount", "blockedCount"):
            if tasks.get(k) not in (None, 0, "0"):
                priorities.append(f"Paperclip {k}: {tasks.get(k)}")
        # Always surface open work if counts exist but keys were unexpected
        if not any(str(p).startswith("Paperclip ") for p in priorities) and issues:
            priorities.append(f"Paperclip tasks snapshot: {issues}")
    if archive_pending:
        priorities.append(
            f"{archive_pending} archive item(s) pending/blocked — ask clarifying questions (Archive tab)."
        )
    jkpi = _jarvis_kpi()
    if int(jkpi.get("awaiting_boss") or 0):
        priorities.append(
            f"{jkpi['awaiting_boss']} Jarvis process(es) awaiting Boss plan approval."
        )
    if int(jkpi.get("failed") or 0):
        priorities.append(f"{jkpi['failed']} Jarvis process(es) failed today.")
    if not priorities:
        priorities.append("No urgent overwatch items. Review Clawsum chat + Boss backlog.")

    agent_brief_path = Path("/docker/clawsum/data/reports/agent-daily-briefs.json")
    agent_briefs: list[Any] = []
    hermes_alerts: list[str] = []
    if agent_brief_path.is_file():
        try:
            packed = json.loads(agent_brief_path.read_text(encoding="utf-8"))
            agent_briefs = packed.get("briefs") or []
            hermes_alerts = [str(a) for a in (packed.get("hermes_alerts") or []) if a]
            for alert in hermes_alerts[:3]:
                line = f"Hermes: {alert}"
                if line not in priorities:
                    priorities.insert(0, line)
        except Exception:
            pass

    return JSONResponse(
        {
            "ok": True,
            "source": "live",
            "priorities": priorities,
            "agent_briefs": agent_briefs,
            "hermes_alerts": hermes_alerts,
            "pending_approvals": approvals_pending,
            "business_cells": businesses,
            "archive_pending": archive_pending,
            "jarvis": jkpi,
            "paperclip": tasks,
            "paperclip_note": paperclip_note or None,
            "paperclip_error": paperclip_error or None,
            "links": links(),
        }
    )


def _paperclip_api() -> str:
    return _env("PAPERCLIP_API", "http://127.0.0.1:3100/api").rstrip("/")


def _paperclip_company_id() -> str:
    company = _env("PAPERCLIP_COMPANY_ID")
    if company:
        return company
    companies = _http_json(f"{_paperclip_api()}/companies")
    if isinstance(companies, list) and companies:
        claw = next(
            (
                c
                for c in companies
                if isinstance(c, dict)
                and str(c.get("name") or "").lower() == "clawsum"
            ),
            None,
        )
        pick = claw if isinstance(claw, dict) else companies[0]
        if isinstance(pick, dict) and pick.get("id"):
            return str(pick["id"])
    return ""


def _paperclip_issues(limit: int = 80) -> list[dict[str, Any]]:
    company = _paperclip_company_id()
    if not company:
        return []
    data = _http_json(f"{_paperclip_api()}/companies/{company}/issues?limit={limit}")
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def _section_from_last_session(raw: str, heading: str) -> str:
    marker = f"## {heading}"
    if marker not in raw:
        return ""
    part = raw.split(marker, 1)[1]
    part = part.split("## ", 1)[0].strip()
    return part[:1200]


def _load_greetings_file() -> dict[str, list[str]]:
    candidates = [
        _hermes_home() / "greetings.json",
        Path("/docker/clawsum/examples/hermes-cockpit/greetings.json"),
        Path("/docker/clawsum/paperclip-data/.hermes/greetings.json"),
    ]
    for p in candidates:
        try:
            if p.is_file():
                data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
                return {
                    "greetings": [str(x).strip() for x in (data.get("greetings") or []) if str(x).strip()],
                    "acks": [str(x).strip() for x in (data.get("acks") or []) if str(x).strip()],
                }
        except (OSError, json.JSONDecodeError, TypeError):
            continue
    return {}


def _boss_greeting_pool() -> list[str]:
    """Approved session / brief openers — text on screen + TTS. Do not invent new ones."""
    file_pool = _load_greetings_file().get("greetings") or []
    if file_pool:
        return file_pool
    return [
        "Good morning, Boss — Clawsum Agent online and at your service.",
        "Welcome back, Gerald. Your briefing is ready.",
        "Standing by, Chief.",
        "At your command, Captain.",
        "Online for you, Commander.",
        "Ready when you are, Sir.",
        "Briefing mode, Boss.",
        "Good afternoon, Gerald — what should we drive first?",
        "Evening check-in, Boss. Here's the board.",
        "Principal — Clawsum Agent reporting.",
        "Fearless leader, the queue is loaded.",
        "Head of the house — session report follows.",
        "Maestro, the baton is yours.",
        "Gerald — unique open, same mission.",
        "Boss, let's move the highest-leverage item.",
        "Sir — your command desk is live.",
        "Chief, progress since last session is below.",
        "Captain, Clawsum Agent standing by for orders.",
        "Hello Boss — I'm here. One moment while I sync.",
        "Acknowledged, Gerald. Pulling your board now.",
        "Clawsum online. Good to see you, Boss.",
        "Standing by for orders, Chief — loading insight.",
    ]


def _boss_ack_pool() -> list[str]:
    """Approved first-line acknowledgements before any tool/search/read."""
    file_pool = _load_greetings_file().get("acks") or []
    if file_pool:
        return file_pool
    return [
        "On it, Boss.",
        "Acknowledged — checking now.",
        "Got it, Gerald. Working.",
        "Understood, Chief. One moment.",
        "Copy that, Captain.",
        "Yes Sir — on it.",
        "Heard. Pulling that up.",
        "Right away, Boss.",
        "Locked in — starting.",
        "Roger that. Standing by with results shortly.",
        "Affirmative. Digging in.",
        "I'm on it, Commander.",
    ]


def _tts_cache_slug(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:12]


def _tts_cache_paths(slug: str) -> list[Path]:
    return [
        _hermes_home() / "audio_cache" / "greetings" / f"{slug}.mp3",
        Path("/docker/clawsum/paperclip-data/.hermes/audio_cache/greetings") / f"{slug}.mp3",
    ]


def _tts_cache_lookup(text: str) -> Path | None:
    slug = _tts_cache_slug(text)
    for p in _tts_cache_paths(slug):
        try:
            if p.is_file() and p.stat().st_size > 100:
                return p
        except OSError:
            continue
    return None


def _voice_cache_entries() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for kind, pool in (("greeting", _boss_greeting_pool()), ("ack", _boss_ack_pool())):
        for text in pool:
            path = _tts_cache_lookup(text)
            if not path:
                continue
            sid = _tts_cache_slug(text)
            out.append(
                {
                    "kind": kind,
                    "text": text,
                    "id": sid,
                    "url": f"/api/plugins/clawsum-cockpit/tts/cache/{sid}",
                }
            )
    return out



@router.get("/session-startup")
def session_startup() -> JSONResponse:
    """Comprehensive session briefing for dock, Brief tab, and Hermes prompts."""
    greetings = _boss_greeting_pool()
    acks = _boss_ack_pool()
    brief_prompt = (
        "FIRST LINE ONLY from the approved greeting pool (no tools yet). "
        "Then deliver the full Session Startup Brief in this exact order: "
        "(1) that greeting already sent, "
        "(2) last session summary, "
        "(3) progress since last session, "
        "(4) active tasks, "
        "(5) upcoming tasks, "
        "(6) recommended Next actions from all live data. "
        "Archive the brief after. Do not invent work."
    )
    suggestions = [
        {"label": "Startup brief", "text": brief_prompt},
        {"label": "What's on fire?", "text": "What's on fire right now? Rank by urgency and say the single best Next."},
        {"label": "CEO brief", "text": brief_prompt},
        {"label": "Inbox triage", "text": "Triage clawsums@gmail.com — list needs_boss items with recommended replies."},
        {"label": "Approvals", "text": "List pending ops.approvals and ask me for decide/reject on the top one."},
        {"label": "Archive queue", "text": "What ChatGPT-archive items need my clarification next?"},
        {"label": "Wrap session", "text": "Wrap up this session: rewrite LAST_SESSION.md and confirm tomorrow's #1 Next."},
    ]

    # --- LAST_SESSION.md ---
    last_raw = ""
    last_summary = ""
    last_done = ""
    last_open = ""
    last_risks = ""
    last_path = _hermes_home() / "LAST_SESSION.md"
    last_mtime = None
    try:
        if last_path.is_file():
            last_raw = last_path.read_text(encoding="utf-8", errors="replace").strip()
            last_mtime = datetime.fromtimestamp(last_path.stat().st_mtime, tz=timezone.utc)
            last_summary = _section_from_last_session(last_raw, "Summary") or last_raw[:800]
            last_done = _section_from_last_session(last_raw, "Done recently")
            last_open = _section_from_last_session(last_raw, "Open for next session")
            last_risks = _section_from_last_session(last_raw, "Risks")
            age_days = max(0, int((datetime.now(timezone.utc) - last_mtime).total_seconds() // 86400))
            stamp = last_mtime.astimezone().strftime("%Y-%m-%d")
            if age_days >= 2:
                last_summary = f"(Handoff file dated {stamp}, {age_days}d stale — wrap session to refresh.) {last_summary}"
            else:
                last_summary = f"(Handoff {stamp}) {last_summary}"
    except OSError:
        pass
    if not last_summary:
        last_summary = "No handoff on file — fresh start."

    # --- Paperclip issues ---
    issues = _paperclip_issues(100)
    active_statuses = {"todo", "in_progress", "inProgress", "doing", "active", "blocked"}
    upcoming_statuses = {"backlog", "planned", "ready", "triage"}
    active_tasks: list[dict[str, Any]] = []
    upcoming_tasks: list[dict[str, Any]] = []
    for iss in issues:
        st = str(iss.get("status") or "").lower()
        item = {
            "identifier": iss.get("identifier") or iss.get("id"),
            "title": iss.get("title") or "untitled",
            "status": iss.get("status"),
            "priority": iss.get("priority"),
        }
        if st in active_statuses or st.replace("_", "") in {"inprogress"}:
            active_tasks.append(item)
        elif st in upcoming_statuses or st == "backlog":
            upcoming_tasks.append(item)
    # Prefer high-priority upcoming first
    pri_rank = {"urgent": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
    upcoming_tasks.sort(
        key=lambda t: pri_rank.get(str(t.get("priority") or "none").lower(), 5)
    )
    active_tasks = active_tasks[:12]
    upcoming_tasks = upcoming_tasks[:12]
    # If nothing "active", surface top high-priority backlog as active focus
    if not active_tasks and upcoming_tasks:
        active_tasks = [t for t in upcoming_tasks if str(t.get("priority") or "").lower() in ("urgent", "high")][:8]
        if not active_tasks:
            active_tasks = upcoming_tasks[:5]

    # --- live ops ---
    brief_payload = brief()
    brief_data: dict[str, Any] = {}
    if hasattr(brief_payload, "body"):
        try:
            brief_data = json.loads(
                brief_payload.body.decode()
                if isinstance(brief_payload.body, (bytes, bytearray))
                else brief_payload.body
            )
        except Exception:
            brief_data = {}
    elif isinstance(brief_payload, dict):
        brief_data = brief_payload

    pending_approvals = int(brief_data.get("pending_approvals") or 0)
    archive_pending = int(brief_data.get("archive_pending") or 0)
    business_cells = int(brief_data.get("business_cells") or 0)
    paperclip = brief_data.get("paperclip") or {}

    inbox_needs = 0
    inbox_samples: list[str] = []
    mailbox = _env("GMAIL_ADMIN_ADDRESS", "clawsums@gmail.com")
    try:
        import psycopg2  # type: ignore

        conn = psycopg2.connect(
            host=_env("POSTGRES_HOST", "127.0.0.1"),
            port=int(_env("POSTGRES_PORT", "5432") or "5432"),
            user=_env("POSTGRES_USER", "clawsum"),
            password=_env("POSTGRES_PASSWORD", ""),
            dbname=_env("POSTGRES_DB", "clawsum"),
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT count(*) FROM ops.emails
                    WHERE (mailbox IS NULL OR mailbox = %s)
                      AND COALESCE(review_status, '') IN ('needs_boss', 'action_required')
                    """,
                    (mailbox,),
                )
                inbox_needs = int(cur.fetchone()[0])
                cur.execute(
                    """
                    SELECT COALESCE(subject, '(no subject)')
                    FROM ops.emails
                    WHERE (mailbox IS NULL OR mailbox = %s)
                      AND COALESCE(review_status, '') IN ('needs_boss', 'action_required')
                    ORDER BY received_at DESC NULLS LAST
                    LIMIT 5
                    """,
                    (mailbox,),
                )
                inbox_samples = [str(r[0])[:100] for r in cur.fetchall()]
        conn.close()
    except Exception:
        pass

    # --- progress since last session ---
    progress: list[str] = []
    if last_done:
        progress.append(last_done.replace("\n", " ").strip()[:400])
    agents = (paperclip.get("agents") or {}) if isinstance(paperclip, dict) else {}
    issues_counts = (paperclip.get("issues") or {}) if isinstance(paperclip, dict) else {}
    if isinstance(issues_counts, dict) and issues_counts:
        progress.append(
            "Paperclip counts: "
            + ", ".join(f"{k}={v}" for k, v in list(issues_counts.items())[:6])
        )
    if isinstance(agents, dict) and agents:
        progress.append(
            "Agents: " + ", ".join(f"{k}={v}" for k, v in list(agents.items())[:6])
        )
    if pending_approvals:
        progress.append(f"{pending_approvals} pending approval(s) in overwatch.")
    jarvis = _jarvis_kpi()
    if int(jarvis.get("awaiting_boss") or 0):
        progress.append(
            f"{jarvis['awaiting_boss']} Jarvis process(es) awaiting Boss (plan gate)."
        )
    if int(jarvis.get("failed") or 0):
        progress.append(f"{jarvis['failed']} Jarvis process(es) failed today.")
    if inbox_needs:
        progress.append(f"{inbox_needs} inbox item(s) need Boss.")
    if archive_pending:
        progress.append(f"{archive_pending} archive item(s) pending/blocked.")
    if not progress:
        progress.append("Not enough live delta yet — treat as fresh start.")

    # --- recommended next ---
    next_actions: list[str] = []
    if int(jarvis.get("awaiting_boss") or 0):
        next_actions.append(
            f"Review Jarvis Processes ({jarvis['awaiting_boss']} awaiting) — approve/reject plans before commands."
        )
    if pending_approvals:
        next_actions.append(
            f"Decide the top pending approval ({pending_approvals} waiting) in Approvals."
        )
    if inbox_needs:
        next_actions.append(
            f"Triage inbox needs_boss ({inbox_needs}) — start with: "
            + (inbox_samples[0] if inbox_samples else "Inbox tab")
        )
    if active_tasks:
        t0 = active_tasks[0]
        next_actions.append(
            f"Drive {t0.get('identifier')}: {t0.get('title')} "
            f"(status={t0.get('status')}, priority={t0.get('priority')})."
        )
    elif upcoming_tasks:
        t0 = upcoming_tasks[0]
        next_actions.append(
            f"Pull {t0.get('identifier')} from backlog: {t0.get('title')}."
        )
    if archive_pending:
        next_actions.append("Clear blocked/pending ChatGPT-archive clarifications.")
    if last_open:
        first_open = next(
            (ln.strip(" -*\t") for ln in last_open.splitlines() if ln.strip()),
            "",
        )
        if first_open and first_open not in " ".join(next_actions):
            next_actions.append(f"From last handoff: {first_open[:160]}")
    if last_risks and "none" not in last_risks.lower()[:40]:
        next_actions.append(f"Watch risk: {last_risks.splitlines()[0].strip()[:140]}")
    if not next_actions:
        next_actions.append("Open Start hub and ask Clawsum for a live triage pass.")

    report_lines = progress[:6] + [
        f"Active focus: {len(active_tasks)} · Upcoming: {len(upcoming_tasks)} · Cells: {business_cells}"
    ]

    # Build markdown briefing (greeting chosen client-side; server includes pool)
    def _fmt_tasks(rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "- none flagged / not enough data"
        out = []
        for r in rows:
            out.append(
                f"- [{r.get('identifier')}] ({r.get('priority')}/{r.get('status')}) {r.get('title')}"
            )
        return "\n".join(out)

    brief_md = "\n".join(
        [
            "# Session Startup Brief",
            "",
            "## Greeting",
            "_(pick one unique line from greetings pool)_",
            "",
            "## Last session",
            last_summary,
            "",
            "## Progress since last session",
            "\n".join(f"- {p}" for p in progress),
            "",
            "## Active tasks",
            _fmt_tasks(active_tasks),
            "",
            "## Upcoming tasks",
            _fmt_tasks(upcoming_tasks),
            "",
            "## Recommended next actions",
            "\n".join(f"{i+1}. {a}" for i, a in enumerate(next_actions)),
            "",
            "## Concerns",
            (last_risks.strip() if last_risks else "none flagged in available sources"),
        ]
    )

    insight = _session_insight_pack(
        last_summary=last_summary,
        last_done=last_done,
        last_open=last_open,
        last_risks=last_risks,
        progress=progress,
        next_actions=next_actions,
        active_tasks=active_tasks,
        upcoming_tasks=upcoming_tasks,
        pending_approvals=pending_approvals,
        inbox_needs=inbox_needs,
        archive_pending=archive_pending,
    )

    return JSONResponse(
        {
            "ok": True,
            "greetings": greetings,
            "acks": acks,
            "ack_rule": (
                "First assistant output must be one approved greeting or ack line "
                "before any tool, search, read, or shell. UI Auto-Speak plays it via TTS."
            ),
            "suggestions": suggestions,
            "brief_prompt": brief_prompt,
            "last_session": last_summary,
            "last_session_done": last_done,
            "last_session_open": last_open,
            "last_session_risks": last_risks,
            "progress": progress,
            "active_tasks": active_tasks,
            "upcoming_tasks": upcoming_tasks,
            "next_actions": next_actions,
            "inbox_needs_boss": inbox_needs,
            "inbox_samples": inbox_samples,
            "report": report_lines,
            "brief_md": brief_md,
            "pending_approvals": pending_approvals,
            "archive_pending": archive_pending,
            "business_cells": business_cells,
            "paperclip": paperclip,
            "jarvis": insight.get("jarvis_kpi") or _jarvis_kpi(),
            "insight": insight,
            "insight_md": insight.get("insight_md"),
            "links": links(),
            "voice": {
                "mode": "elevenlabs_browser",
                "provider": (_env("SPEECH_TTS_PROVIDER", "elevenlabs") or "elevenlabs"),
                "voice_id": (_env("ELEVENLABS_VOICE_ID", "KuQm0Vgf0XGL6Vqko2UY") or "KuQm0Vgf0XGL6Vqko2UY"),
                "hint": "Mic = STT (Chrome/Whisper). Speak = ElevenLabs TTS → browser Audio (cached greetings/acks play instantly).",
                "cache": _voice_cache_entries(),
            },
        }
    )


@router.get("/archive")
def archive(limit: int = 12) -> JSONResponse:
    """Proactive ChatGPT-archive brief for Clawsum (questions + drive-forward)."""
    limit = max(1, min(limit, 50))
    try:
        import psycopg2
        import psycopg2.extras  # type: ignore

        conn = psycopg2.connect(
            host=_env("POSTGRES_HOST", "127.0.0.1"),
            port=int(_env("POSTGRES_PORT", "5432") or "5432"),
            user=_env("POSTGRES_USER", "clawsum"),
            password=_env("POSTGRES_PASSWORD", ""),
            dbname=_env("POSTGRES_DB", "clawsum"),
        )
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT scope, work_status, count(*) AS n
                    FROM ops.conversations
                    GROUP BY 1, 2
                    ORDER BY 1, 2
                    """
                )
                counts = [dict(r) for r in cur.fetchall()]
                cur.execute(
                    """
                    SELECT c.title, c.scope, c.work_status, c.intent_summary,
                           c.clarification_questions, c.proactive_flags,
                           c.paperclip_issue_identifier, b.slug AS business_slug
                    FROM ops.conversations c
                    LEFT JOIN ops.businesses b ON b.id = c.primary_business_id
                    WHERE c.scope IN ('business', 'mixed', 'unknown')
                      AND c.work_status IN ('pending', 'blocked', 'in_progress', 'other')
                    ORDER BY
                      CASE c.work_status
                        WHEN 'blocked' THEN 0
                        WHEN 'pending' THEN 1
                        WHEN 'in_progress' THEN 2
                        ELSE 3
                      END,
                      c.updated_at_source DESC NULLS LAST
                    LIMIT %s
                    """,
                    (limit,),
                )
                drive = [dict(r) for r in cur.fetchall()]
                cur.execute(
                    "SELECT count(*) AS n FROM ops.conversations WHERE scope = 'personal'"
                )
                personal_n = int(cur.fetchone()["n"])
        conn.close()
        questions: list[str] = []
        for item in drive:
            for q in item.get("clarification_questions") or []:
                if q and q not in questions:
                    questions.append(q)
        priorities = []
        if any(i.get("work_status") == "blocked" for i in drive):
            priorities.append("Blocked archive items need an unblock decision.")
        if any(i.get("scope") == "unknown" for i in drive):
            priorities.append("Some archive items still need personal vs business scope.")
        if not priorities:
            priorities.append("Review drive-forward archive items and ask clarifying questions.")
        briefs_db = _list_session_briefs_db(limit=12) or []
        briefs_files = _list_session_brief_files(limit=12)
        # Prefer DB rows; fill from files if DB empty / missing migration.
        session_briefs = briefs_db if briefs_db else briefs_files
        return JSONResponse(
            {
                "ok": True,
                "priorities": priorities,
                "counts_by_scope_status": counts,
                "personal_conversations": personal_n,
                "drive_forward": drive,
                "questions_for_boss": questions[:8],
                "session_briefs": session_briefs,
                "session_briefs_count": len(session_briefs),
                "session_briefs_path": str(_session_briefs_dir()),
                "clawsum_instructions": [
                    "Read Paperclip tasks first; link related archive items.",
                    "Ask one sharp question per pending/blocked/unknown item.",
                    "Keep personal scope out of business agents and Clawsum memory.",
                ],
            }
        )
    except Exception as exc:
        briefs_files = _list_session_brief_files(limit=12)
        return JSONResponse(
            {
                "ok": False,
                "drive_forward": [],
                "questions_for_boss": [],
                "session_briefs": briefs_files,
                "session_briefs_count": len(briefs_files),
                "session_briefs_path": str(_session_briefs_dir()),
                "error": str(exc),
                "hint": "Apply postgres-init/13-chatgpt-archive.sql then import/classify/link",
            }
        )


@router.get("/session-briefs")
def session_briefs(limit: int = 50) -> JSONResponse:
    """Archived Session Startup Briefs (Postgres + HERMES_HOME/session-briefs/)."""
    limit = max(1, min(int(limit or 50), 200))
    db_rows = _list_session_briefs_db(limit=limit)
    files = _list_session_brief_files(limit=limit)
    items = db_rows if db_rows else files
    return JSONResponse(
        {
            "ok": True,
            "count": len(items),
            "briefs": items,
            "path": str(_session_briefs_dir()),
            "source": "db" if db_rows else "files",
            "hint": "Boss → Archive tab lists these. Hermes writes after each Session Startup Brief.",
        }
    )


@router.post("/session-briefs")
async def create_session_brief(request: Request) -> JSONResponse:
    """Persist a Session Startup Brief (called by Hermes after delivering BOOT.md)."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    body_md = str(payload.get("body_md") or payload.get("body") or "").strip()
    if not body_md:
        raise HTTPException(status_code=400, detail="body_md required")
    try:
        row = _save_session_brief(
            body_md,
            greeting=str(payload.get("greeting") or "").strip(),
            session_key=str(payload.get("session_key") or "").strip(),
            source=str(payload.get("source") or "hermes").strip() or "hermes",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse({"ok": True, "brief": row})


def _pg_conn():
    import psycopg2

    return psycopg2.connect(
        host=_env("POSTGRES_HOST", "127.0.0.1"),
        port=int(_env("POSTGRES_PORT", "5432") or "5432"),
        user=_env("POSTGRES_USER", "clawsum"),
        password=_env("POSTGRES_PASSWORD", ""),
        dbname=_env("POSTGRES_DB", "clawsum"),
    )


def _jarvis_kpi() -> dict[str, Any]:
    empty = {
        "proposed": 0,
        "running": 0,
        "executed": 0,
        "failed": 0,
        "cancelled": 0,
        "rejected": 0,
        "confirmed": 0,
        "today_total": 0,
        "awaiting_boss": 0,
    }
    try:
        import psycopg2.extras  # type: ignore

        conn = _pg_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT status, count(*)::int AS n
                    FROM ops.jarvis_processes
                    WHERE created_at >= date_trunc('day', now())
                    GROUP BY 1
                    """
                )
                for row in cur.fetchall() or []:
                    st = str(row.get("status") or "")
                    if st in empty:
                        empty[st] = int(row.get("n") or 0)
                empty["today_total"] = sum(
                    empty[k]
                    for k in (
                        "proposed",
                        "confirmed",
                        "running",
                        "executed",
                        "failed",
                        "cancelled",
                        "rejected",
                    )
                )
                empty["awaiting_boss"] = empty["proposed"]
        conn.close()
    except Exception as exc:
        empty["error"] = str(exc)
    return empty


def _read_hermes_md(name: str, limit: int = 8000) -> str:
    try:
        p = _hermes_home() / name
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace").strip()[:limit]
    except OSError:
        pass
    return ""


def _recent_jarvis_processes(limit: int = 12) -> list[dict[str, Any]]:
    try:
        import psycopg2.extras  # type: ignore

        conn = _pg_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id::text, created_at, title, intent, status, mode, skill_id, agent_id, risk_tier
                    FROM ops.jarvis_processes
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = []
                for r in cur.fetchall() or []:
                    d = dict(r)
                    if d.get("created_at") is not None:
                        d["created_at"] = d["created_at"].isoformat()
                    rows.append(d)
        conn.close()
        return rows
    except Exception:
        return []


def _reminders_open(limit: int = 8) -> list[dict[str, Any]]:
    try:
        import psycopg2.extras  # type: ignore

        conn = _pg_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id::text, title, description, due_date, priority, source
                    FROM ops.reminders
                    WHERE completed_at IS NULL
                      AND (snoozed_until IS NULL OR snoozed_until < CURRENT_DATE)
                    ORDER BY due_date NULLS LAST, id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = []
                for r in cur.fetchall() or []:
                    d = dict(r)
                    if d.get("due_date") is not None:
                        d["due_at"] = d["due_date"].isoformat()
                        d["due_date"] = d["due_at"]
                    rows.append(d)
        conn.close()
        return rows
    except Exception:
        return []


def _session_insight_pack(
    *,
    last_summary: str,
    last_done: str,
    last_open: str,
    last_risks: str,
    progress: list[str],
    next_actions: list[str],
    active_tasks: list[dict[str, Any]],
    upcoming_tasks: list[dict[str, Any]],
    pending_approvals: int,
    inbox_needs: int,
    archive_pending: int,
) -> dict[str, Any]:
    """Full catch-up blob for Hermes — no tool calls needed at session start."""
    memory_md = _read_hermes_md("MEMORY.md")
    last_raw = _read_hermes_md("LAST_SESSION.md")
    user_md = _read_hermes_md("USER.md", 2500)
    jarvis_rows = _recent_jarvis_processes(12)
    reminders = _reminders_open(8)
    jarvis = _jarvis_kpi()
    owner = {
        "holding": "Hennessey Holdings LLC",
        "boss": "Gerald Allan Hennessey",
        "ops_brand": "Clawsum",
    }
    lines = [
        "# Jarvis session insight (preloaded — do not re-fetch with tools)",
        "",
        f"- Owner holding: **{owner['holding']}**",
        f"- Master Boss: **{owner['boss']}**",
        f"- Ops brand: **{owner['ops_brand']}**",
        "",
        "## Live pulse",
        f"- Pending overwatch approvals: {pending_approvals}",
        f"- Inbox needs Boss: {inbox_needs}",
        f"- Archive pending/blocked: {archive_pending}",
        f"- Jarvis awaiting Boss (proposals only): {jarvis.get('awaiting_boss', 0)}",
        f"- Jarvis failed today: {jarvis.get('failed', 0)}",
        f"- Jarvis executed today: {jarvis.get('executed', 0)}",
        "",
        "## Progress",
        *[f"- {p}" for p in (progress or ["not enough data"])],
        "",
        "## Recommended next",
        *[f"{i+1}. {a}" for i, a in enumerate(next_actions or ["none flagged"])],
        "",
        "## Active tasks",
    ]
    if active_tasks:
        for t in active_tasks[:8]:
            lines.append(
                f"- [{t.get('identifier')}] {t.get('title')} ({t.get('status')}/{t.get('priority')})"
            )
    else:
        lines.append("- none flagged")
    lines += ["", "## Upcoming tasks"]
    if upcoming_tasks:
        for t in upcoming_tasks[:8]:
            lines.append(
                f"- [{t.get('identifier')}] {t.get('title')} ({t.get('status')}/{t.get('priority')})"
            )
    else:
        lines.append("- none flagged")
    lines += ["", "## Reminders"]
    if reminders:
        for r in reminders:
            lines.append(f"- {r.get('title') or r.get('id')} (due {r.get('due_at') or 'n/a'})")
    else:
        lines.append("- none flagged")
    lines += ["", "## Recent Jarvis processes"]
    if jarvis_rows:
        for p in jarvis_rows[:8]:
            lines.append(
                f"- [{p.get('status')}/{p.get('mode')}] {p.get('title')}"
            )
    else:
        lines.append("- none yet")
    lines += [
        "",
        "## Last session summary",
        last_summary or "fresh start",
        "",
        "### Done recently",
        last_done or "not enough data",
        "",
        "### Open for next session",
        last_open or "not enough data",
        "",
        "### Risks",
        last_risks or "none flagged",
        "",
        "## MEMORY.md (executive ranking)",
        memory_md or "not enough data",
        "",
        "## Gate rules (W2)",
        "- Default: batch_gate — propose ALL executes up front, wait for **Approve All once**, then run every step with NO drip approvals.",
        "- Preapproved skills → confirmation chip only.",
        "- skip_batch / just-do-it only when Gerald explicitly says so.",
    ]
    return {
        "owner": owner,
        "memory_md": memory_md,
        "last_session_md": last_raw,
        "user_md": user_md,
        "jarvis_kpi": jarvis,
        "jarvis_recent": jarvis_rows,
        "reminders": reminders,
        "insight_md": "\n".join(lines),
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "instruction": (
            "Use insight_md as your catch-up. Do not run shell/SQL/tool calls just to "
            "rediscover board state that is already in this payload."
        ),
    }


def _match_preapproved(intent: str, skill_id: str = "", agent_id: str = "") -> dict[str, Any] | None:
    intent_l = (intent or "").lower()
    skill_id = (skill_id or "").strip()
    try:
        import psycopg2.extras  # type: ignore

        conn = _pg_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id::text, skill_id, agent_id, title, match_patterns, max_tier
                    FROM ops.jarvis_preapproved
                    WHERE enabled = true
                    ORDER BY max_tier ASC, title ASC
                    """
                )
                rows = list(cur.fetchall() or [])
        conn.close()
    except Exception:
        return None
    for row in rows:
        if skill_id and str(row.get("skill_id")) == skill_id:
            if not agent_id or not row.get("agent_id") or str(row.get("agent_id")) == agent_id:
                return dict(row)
        pats = row.get("match_patterns") or []
        for pat in pats:
            if pat and str(pat).lower() in intent_l:
                return dict(row)
    return None


@router.get("/processes/kpi")
def processes_kpi() -> JSONResponse:
    return JSONResponse({"ok": True, "kpi": _jarvis_kpi()})


@router.get("/processes")
def list_processes(limit: int = 50, status: str = "") -> JSONResponse:
    limit = max(1, min(int(limit or 50), 200))
    status = (status or "").strip().lower()
    try:
        import psycopg2.extras  # type: ignore

        conn = _pg_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if status:
                    cur.execute(
                        """
                        SELECT id::text, created_at, updated_at, session_key, title, intent,
                               plan_md, status, mode, skill_id, agent_id, risk_tier,
                               result_md, error_text, approved_at, started_at, finished_at, meta
                        FROM ops.jarvis_processes
                        WHERE status = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (status, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id::text, created_at, updated_at, session_key, title, intent,
                               plan_md, status, mode, skill_id, agent_id, risk_tier,
                               result_md, error_text, approved_at, started_at, finished_at, meta
                        FROM ops.jarvis_processes
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                rows = []
                for r in cur.fetchall() or []:
                    d = dict(r)
                    for k in ("created_at", "updated_at", "approved_at", "started_at", "finished_at"):
                        if d.get(k) is not None:
                            d[k] = d[k].isoformat()
                    rows.append(d)
        conn.close()
        return JSONResponse({"ok": True, "count": len(rows), "processes": rows, "kpi": _jarvis_kpi()})
    except Exception as exc:
        return JSONResponse(
            {"ok": False, "error": str(exc), "processes": [], "kpi": _jarvis_kpi()},
            status_code=500,
        )


@router.post("/processes")
async def create_process(request: Request) -> JSONResponse:
    """Jarvis logs a requested process.

    Modes:
      - batch_gate (default for non-trivial work): full step list → one Approve All → run all.
      - preapproved_fast: matches ops.jarvis_preapproved — confirmation chip only.
      - plan_gate: legacy alias for batch_gate (unsolicited proposals).
      - boss_ordered: only when skip_batch / explicit just-do-it — no Approve All.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    title = str(payload.get("title") or "").strip()
    intent = str(payload.get("intent") or payload.get("request") or "").strip()
    plan_md = str(payload.get("plan_md") or payload.get("plan") or "").strip()
    skill_id = str(payload.get("skill_id") or "").strip()
    agent_id = str(payload.get("agent_id") or "").strip()
    session_key = str(payload.get("session_key") or "").strip()
    source = str(payload.get("source") or "").strip().lower()
    try:
        risk_tier = int(payload.get("risk_tier") if payload.get("risk_tier") is not None else 1)
    except (TypeError, ValueError):
        risk_tier = 1
    if not title:
        title = (intent[:80] if intent else "Jarvis process")
    if not intent and not plan_md:
        raise HTTPException(status_code=400, detail="intent or plan_md required")

    # Normalize steps: [{title, detail?, status?}]
    raw_steps = payload.get("steps") or payload.get("executes") or []
    steps: list[dict[str, Any]] = []
    if isinstance(raw_steps, list):
        for i, s in enumerate(raw_steps):
            if isinstance(s, str):
                steps.append({"n": i + 1, "title": s[:200], "detail": "", "status": "pending"})
            elif isinstance(s, dict):
                steps.append(
                    {
                        "n": i + 1,
                        "title": str(s.get("title") or s.get("name") or f"Step {i+1}")[:200],
                        "detail": str(s.get("detail") or s.get("cmd") or s.get("command") or "")[:800],
                        "status": "pending",
                    }
                )
    if steps and not plan_md:
        plan_md = "## Batch execute plan\n\n" + "\n".join(
            f"{s['n']}. **{s['title']}**" + (f" — {s['detail']}" if s.get("detail") else "")
            for s in steps
        )

    skip_batch = bool(
        payload.get("skip_batch")
        or payload.get("just_do_it")
        or source in ("skip_batch", "just_do_it")
    )
    force_plan = bool(payload.get("force_plan_gate") or payload.get("force_batch_gate"))
    jarvis_proposal = force_plan or source in (
        "jarvis_proposal",
        "proposal",
        "unsolicited",
        "suggest",
        "suggested",
    )

    match = _match_preapproved(intent or title, skill_id, agent_id)

    if match and not force_plan and not steps:
        mode = "preapproved_fast"
        status = "confirmed"
        skill_id = skill_id or str(match.get("skill_id") or "")
        agent_id = agent_id or str(match.get("agent_id") or "")
        if not plan_md:
            plan_md = (
                f"Preapproved skill: **{match.get('title')}** (`{skill_id}`). "
                "Confirmation chip only."
            )
    elif skip_batch and not jarvis_proposal:
        mode = "boss_ordered"
        status = "confirmed"
        if not plan_md:
            plan_md = "Skip-batch / just-do-it. Short confirm, then execute."
    else:
        # Default: full batch plan, one Approve All — no drip-feed approvals
        mode = "batch_gate"
        status = "proposed"
        if not plan_md:
            plan_md = (
                "Batch execute plan — list every step, wait for **Approve All**, "
                "then run with no further prompts."
            )
        if not steps:
            # Encourage structured steps even if only plan_md provided
            steps = [{"n": 1, "title": title[:200], "detail": intent[:800], "status": "pending"}]

    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    meta = dict(meta)
    meta.setdefault(
        "source",
        source
        or (
            "jarvis_proposal"
            if jarvis_proposal
            else ("boss_order" if mode == "boss_ordered" else "batch")
        ),
    )
    meta["steps"] = steps
    meta["batch"] = mode == "batch_gate"
    meta["approve_all"] = mode == "batch_gate"
    try:
        import json as _json
        import psycopg2.extras  # type: ignore

        conn = _pg_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO ops.jarvis_processes
                      (session_key, title, intent, plan_md, status, mode, skill_id, agent_id, risk_tier, meta, approved_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb, CASE WHEN %s = 'confirmed' THEN now() ELSE NULL END)
                    RETURNING id::text, created_at, status, mode, skill_id, agent_id, title, plan_md, risk_tier, meta
                    """,
                    (
                        session_key or None,
                        title,
                        intent or None,
                        plan_md or None,
                        status,
                        mode,
                        skill_id or None,
                        agent_id or None,
                        risk_tier,
                        _json.dumps(meta),
                        status,
                    ),
                )
                row = dict(cur.fetchone())
                if row.get("created_at") is not None:
                    row["created_at"] = row["created_at"].isoformat()
                if isinstance(row.get("meta"), str):
                    try:
                        row["meta"] = _json.loads(row["meta"])
                    except Exception:
                        pass
        conn.close()
        needs_approval = mode in ("batch_gate", "plan_gate")
        confirm_only = mode in ("preapproved_fast", "boss_ordered")
        hints = {
            "batch_gate": (
                "Present the FULL step checklist. Wait for Approve All once. "
                "Then execute every step with NO further approval prompts."
            ),
            "plan_gate": (
                "Present the FULL step checklist. Wait for Approve All once. "
                "Then execute every step with NO further approval prompts."
            ),
            "preapproved_fast": "Show short confirmation chip — executing preapproved skill.",
            "boss_ordered": "Skip-batch authorized. Confirm briefly, then execute — no drip approvals.",
        }
        return JSONResponse(
            {
                "ok": True,
                "process": row,
                "needs_boss_approval": needs_approval,
                "approve_all": needs_approval,
                "show_confirmation_only": confirm_only,
                "boss_ordered": mode == "boss_ordered",
                "batch": mode == "batch_gate",
                "steps": steps,
                "preapproved": match,
                "hint": hints.get(mode, ""),
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/processes/{process_id}/steps/{step_n}/complete")
async def complete_process_step(process_id: str, step_n: int, request: Request) -> JSONResponse:
    """Mark one batch step done/failed without asking Boss again."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    st = str(payload.get("status") or "executed").strip().lower()
    if st not in ("executed", "failed", "skipped", "running"):
        raise HTTPException(status_code=400, detail="status must be executed|failed|skipped|running")
    note = str(payload.get("note") or payload.get("result") or "").strip()
    try:
        import json as _json
        import psycopg2.extras  # type: ignore

        conn = _pg_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT id::text, meta, status FROM ops.jarvis_processes WHERE id = %s::uuid",
                    (process_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="process not found")
                meta = row.get("meta") or {}
                if isinstance(meta, str):
                    meta = _json.loads(meta)
                if not isinstance(meta, dict):
                    meta = {}
                steps = list(meta.get("steps") or [])
                found = False
                for s in steps:
                    if int(s.get("n") or 0) == int(step_n):
                        s["status"] = st
                        if note:
                            s["note"] = note[:1000]
                        found = True
                        break
                if not found:
                    raise HTTPException(status_code=404, detail=f"step {step_n} not found")
                meta["steps"] = steps
                new_status = row.get("status")
                if new_status == "confirmed":
                    new_status = "running"
                cur.execute(
                    """
                    UPDATE ops.jarvis_processes
                    SET meta = %s::jsonb,
                        status = %s,
                        updated_at = now(),
                        started_at = COALESCE(started_at, now())
                    WHERE id = %s::uuid
                    RETURNING id::text, status, meta
                    """,
                    (_json.dumps(meta), new_status, process_id),
                )
                out = dict(cur.fetchone())
        conn.close()
        return JSONResponse({"ok": True, "process": out, "step": step_n, "step_status": st})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/processes/{process_id}/decide")
async def decide_process(process_id: str, request: Request) -> JSONResponse:
    """Boss approve/reject/cancel a proposed Jarvis process."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    decision = str(payload.get("decision") or payload.get("status") or "").strip().lower()
    mapping = {
        "approve": "confirmed",
        "approved": "confirmed",
        "confirm": "confirmed",
        "confirmed": "confirmed",
        "reject": "rejected",
        "rejected": "rejected",
        "cancel": "cancelled",
        "cancelled": "cancelled",
        "canceled": "cancelled",
    }
    new_status = mapping.get(decision)
    if not new_status:
        raise HTTPException(status_code=400, detail="decision must be approve|reject|cancel")
    try:
        import psycopg2.extras  # type: ignore

        conn = _pg_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE ops.jarvis_processes
                    SET status = %s,
                        updated_at = now(),
                        approved_at = CASE WHEN %s = 'confirmed' THEN now() ELSE approved_at END
                    WHERE id = %s::uuid AND status IN ('proposed', 'confirmed')
                    RETURNING id::text, title, status, mode, skill_id, agent_id, plan_md, risk_tier
                    """,
                    (new_status, new_status, process_id),
                )
                row = cur.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="process not found or not decidable")
        return JSONResponse({"ok": True, "process": dict(row), "kpi": _jarvis_kpi()})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/processes/{process_id}/complete")
async def complete_process(process_id: str, request: Request) -> JSONResponse:
    """Mark a process executed or failed after work finishes."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    ok_flag = payload.get("ok")
    status = str(payload.get("status") or ("executed" if ok_flag is not False else "failed")).strip().lower()
    if status not in ("executed", "failed", "running"):
        raise HTTPException(status_code=400, detail="status must be running|executed|failed")
    result_md = str(payload.get("result_md") or payload.get("result") or "").strip()
    error_text = str(payload.get("error") or payload.get("error_text") or "").strip()
    try:
        import psycopg2.extras  # type: ignore

        conn = _pg_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE ops.jarvis_processes
                    SET status = %s,
                        updated_at = now(),
                        started_at = CASE
                          WHEN %s = 'running' AND started_at IS NULL THEN now()
                          WHEN started_at IS NULL AND %s IN ('executed','failed') THEN now()
                          ELSE started_at END,
                        finished_at = CASE WHEN %s IN ('executed','failed') THEN now() ELSE finished_at END,
                        result_md = COALESCE(NULLIF(%s, ''), result_md),
                        error_text = COALESCE(NULLIF(%s, ''), error_text)
                    WHERE id = %s::uuid
                    RETURNING id::text, title, status, mode, skill_id, agent_id
                    """,
                    (status, status, status, status, result_md, error_text, process_id),
                )
                row = cur.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="process not found")
        return JSONResponse({"ok": True, "process": dict(row), "kpi": _jarvis_kpi()})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/preapproved")
def list_preapproved() -> JSONResponse:
    try:
        import psycopg2.extras  # type: ignore

        conn = _pg_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id::text, skill_id, agent_id, title, match_patterns, max_tier, enabled, created_at
                    FROM ops.jarvis_preapproved
                    ORDER BY max_tier ASC, title ASC
                    """
                )
                rows = []
                for r in cur.fetchall() or []:
                    d = dict(r)
                    if d.get("created_at") is not None:
                        d["created_at"] = d["created_at"].isoformat()
                    rows.append(d)
        conn.close()
        return JSONResponse({"ok": True, "preapproved": rows})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc), "preapproved": []}, status_code=500)


@router.post("/voice-debug")
async def voice_debug(request: Request) -> JSONResponse:
    """Client voice/listen diagnostics — append to log for Boss troubleshooting."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    import datetime as _dt
    line = {
        "ts": _dt.datetime.utcnow().isoformat() + "Z",
        "event": str(payload.get("event") or "event"),
        "detail": payload.get("detail"),
        "transcript_len": payload.get("transcript_len"),
        "listen_on": payload.get("listen_on"),
        "secure": payload.get("secure"),
        "speech_rec": payload.get("speech_rec"),
        "user_agent": (request.headers.get("user-agent") or "")[:160],
    }
    try:
        from pathlib import Path as _P
        log_path = _P("/paperclip/logs/voice-debug.log")
        # also try host-mounted path if present
        alts = [log_path, _P("/docker/clawsum/logs/voice-debug.log"), _P("/tmp/voice-debug.log")]
        written = False
        for p in alts:
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                with p.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(line, ensure_ascii=False) + "\n")
                written = True
                break
            except Exception:
                continue
        print("VOICE_DEBUG", json.dumps(line, ensure_ascii=False), flush=True)
        return JSONResponse({"ok": True, "logged": written})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})


@router.get("/tts/cache/{slug}")
def tts_cache_get(slug: str) -> Response:
    """Serve pre-generated greeting/ack MP3 for immediate playback."""
    import re

    if not re.fullmatch(r"[a-f0-9]{12}", slug or ""):
        raise HTTPException(status_code=400, detail="invalid slug")
    for p in _tts_cache_paths(slug):
        try:
            if p.is_file():
                return Response(
                    content=p.read_bytes(),
                    media_type="audio/mpeg",
                    headers={
                        "Content-Type": "audio/mpeg",
                        "Cache-Control": "public, max-age=86400",
                        "X-Clawsum-TTS-Provider": "cache",
                        "X-Clawsum-TTS-Cache-Id": slug,
                    },
                )
        except OSError:
            continue
    raise HTTPException(status_code=404, detail="cache miss")


@router.post("/tts")
async def tts_speak(request: Request) -> Response:
    """Synthesize speech for browser playback.

    Prefer disk cache (pre-generated greetings/acks) → ElevenLabs → OpenAI.
    Returns audio/mpeg bytes — never expose API keys to the browser.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    text = str(payload.get("text") or payload.get("input") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    # Cap length — briefs can be long; keep latency/cost sane
    max_chars = int(_env("CLAWSUM_TTS_MAX_CHARS", "2500") or "2500")
    text = text[:max_chars]

    # Instant path for approved greetings/acks
    cached = _tts_cache_lookup(text)
    if cached is not None:
        try:
            audio = cached.read_bytes()
            return Response(
                content=audio,
                media_type="audio/mpeg",
                headers={
                    "Content-Type": "audio/mpeg",
                    "Cache-Control": "public, max-age=86400",
                    "X-Clawsum-TTS-Provider": "cache",
                    "X-Clawsum-TTS-Cache-Id": _tts_cache_slug(text),
                },
            )
        except OSError:
            pass

    provider = (
        str(payload.get("provider") or "").strip().lower()
        or (_env("SPEECH_TTS_PROVIDER", "elevenlabs") or "elevenlabs").lower()
    )
    el_key = (_env("ELEVENLABS_API_KEY", "") or "").strip()
    voice_id = (
        str(payload.get("voice_id") or "").strip()
        or (_env("ELEVENLABS_VOICE_ID", "KuQm0Vgf0XGL6Vqko2UY") or "KuQm0Vgf0XGL6Vqko2UY")
    )
    oai_key = (
        _env("OPENAI_API_KEY", "") or _env("VOICE_TOOLS_OPENAI_KEY", "") or ""
    ).strip()

    import urllib.error
    import urllib.request as _urlreq

    def _post_bytes(url: str, body: bytes, headers: dict[str, str], timeout: int = 90) -> bytes:
        req = _urlreq.Request(url, data=body, method="POST", headers=headers)
        with _urlreq.urlopen(req, timeout=timeout) as resp:
            return resp.read()

    audio = b""
    used = ""
    err_detail = ""

    if provider in ("elevenlabs", "eleven", "el") or (provider != "openai" and el_key):
        if el_key:
            model = _env("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2") or "eleven_multilingual_v2"
            base = (_env("ELEVENLABS_API_BASE", "https://api.elevenlabs.io/v1") or "https://api.elevenlabs.io/v1").rstrip("/")
            try:
                audio = _post_bytes(
                    f"{base}/text-to-speech/{voice_id}",
                    json.dumps(
                        {
                            "text": text,
                            "model_id": model,
                            "voice_settings": {
                                "stability": float(_env("ELEVENLABS_STABILITY", "0.45") or "0.45"),
                                "similarity_boost": float(
                                    _env("ELEVENLABS_SIMILARITY", "0.8") or "0.8"
                                ),
                            },
                        }
                    ).encode("utf-8"),
                    {
                        "xi-api-key": el_key,
                        "Content-Type": "application/json",
                        "Accept": "audio/mpeg",
                    },
                )
                used = "elevenlabs"
            except urllib.error.HTTPError as exc:
                try:
                    err_detail = exc.read().decode("utf-8", errors="replace")[:400]
                except Exception:
                    err_detail = str(exc)
                print("VOICE_TTS_EL_ERR", getattr(exc, "code", "?"), err_detail, flush=True)
            except Exception as exc:
                err_detail = str(exc)
                print("VOICE_TTS_EL_ERR", err_detail, flush=True)

    if not audio and oai_key:
        try:
            audio = _post_bytes(
                "https://api.openai.com/v1/audio/speech",
                json.dumps(
                    {
                        "model": _env("OPENAI_TTS_MODEL", "gpt-4o-mini-tts") or "gpt-4o-mini-tts",
                        "voice": _env("OPENAI_TTS_VOICE", "alloy") or "alloy",
                        "input": text,
                        "response_format": "mp3",
                    }
                ).encode("utf-8"),
                {
                    "Authorization": f"Bearer {oai_key}",
                    "Content-Type": "application/json",
                },
            )
            used = "openai"
        except urllib.error.HTTPError as exc:
            try:
                err_detail = exc.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                err_detail = str(exc)
            print("VOICE_TTS_OAI_ERR", getattr(exc, "code", "?"), err_detail, flush=True)
        except Exception as exc:
            err_detail = str(exc)
            print("VOICE_TTS_OAI_ERR", err_detail, flush=True)

    if not audio:
        if not el_key and not oai_key:
            return JSONResponse(
                {
                    "ok": False,
                    "error": "No TTS key: set ELEVENLABS_API_KEY (preferred) or OPENAI_API_KEY",
                    "voice_id": voice_id,
                },
                status_code=503,
            )
        return JSONResponse(
            {
                "ok": False,
                "error": "TTS synthesis failed",
                "detail": err_detail,
                "voice_id": voice_id,
            },
            status_code=502,
        )

    print(
        "VOICE_TTS",
        json.dumps(
            {
                "provider": used,
                "voice_id": voice_id if used == "elevenlabs" else None,
                "chars": len(text),
                "bytes": len(audio),
            }
        ),
        flush=True,
    )
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Content-Type": "audio/mpeg",
            "Cache-Control": "no-store",
            "X-Clawsum-TTS-Provider": used,
            "X-Clawsum-TTS-Voice": voice_id if used == "elevenlabs" else "openai",
        },
    )


@router.get("/tts/status")
def tts_status() -> JSONResponse:
    el = bool((_env("ELEVENLABS_API_KEY", "") or "").strip())
    oai = bool((_env("OPENAI_API_KEY", "") or _env("VOICE_TOOLS_OPENAI_KEY", "") or "").strip())
    return JSONResponse(
        {
            "ok": True,
            "provider": (_env("SPEECH_TTS_PROVIDER", "elevenlabs") or "elevenlabs"),
            "voice_id": (_env("ELEVENLABS_VOICE_ID", "KuQm0Vgf0XGL6Vqko2UY") or "KuQm0Vgf0XGL6Vqko2UY"),
            "elevenlabs_configured": el,
            "openai_fallback": oai,
            "ready": el or oai,
        }
    )


@router.post("/transcribe")
async def transcribe_audio(request: Request) -> JSONResponse:
    """Transcribe uploaded audio via OpenAI Whisper (reliable fallback for browser STT)."""
    api_key = (
        _env("OPENAI_API_KEY", "")
        or _env("VOICE_TOOLS_OPENAI_KEY", "")
        or ""
    ).strip()
    if not api_key:
        return JSONResponse(
            {"ok": False, "error": "OPENAI_API_KEY not configured on server"},
            status_code=503,
        )
    try:
        form = await request.form()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"multipart required: {exc}") from exc
    upload = form.get("file") or form.get("audio")
    if upload is None:
        raise HTTPException(status_code=400, detail="file field required")
    try:
        raw = await upload.read()  # type: ignore[attr-defined]
    except Exception:
        raw = getattr(upload, "file", None)
        raw = raw.read() if raw is not None else b""
    if not raw:
        raise HTTPException(status_code=400, detail="empty audio")
    filename = getattr(upload, "filename", None) or "audio.webm"
    content_type = getattr(upload, "content_type", None) or "audio/webm"
    import urllib.error
    import urllib.request as _urlreq

    boundary = "----ClawsumWhisperBoundary7d4a"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="model"\r\n\r\n'
        f"whisper-1\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="language"\r\n\r\n'
        f"en\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="response_format"\r\n\r\n'
        f"json\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + raw + f"\r\n--{boundary}--\r\n".encode("utf-8")
    req = _urlreq.Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with _urlreq.urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        print("VOICE_TRANSCRIBE_ERR", exc.code, err_body, flush=True)
        return JSONResponse(
            {"ok": False, "error": f"OpenAI HTTP {exc.code}", "detail": err_body},
            status_code=502,
        )
    except Exception as exc:
        print("VOICE_TRANSCRIBE_ERR", str(exc), flush=True)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=502)
    text = str(payload.get("text") or "").strip()
    print(
        "VOICE_TRANSCRIBE",
        json.dumps({"bytes": len(raw), "chars": len(text), "file": filename}),
        flush=True,
    )
    return JSONResponse({"ok": True, "text": text, "bytes": len(raw)})


@router.get("/inbox")
def inbox(
    limit: int = 200,
    offset: int = 0,
    view: str = "all",
) -> JSONResponse:
    """clawsums@gmail.com review snapshot — full body + narrative for expandable UI.

    view: all | needs_boss | action | inbox
    """
    limit = max(1, min(int(limit or 200), 500))
    offset = max(0, int(offset or 0))
    view = (view or "all").strip().lower()
    mailbox = _env("GMAIL_ADMIN_ADDRESS", "clawsums@gmail.com")
    try:
        import psycopg2
        import psycopg2.extras  # type: ignore

        conn = psycopg2.connect(
            host=_env("POSTGRES_HOST", "127.0.0.1"),
            port=int(_env("POSTGRES_PORT", "5432") or "5432"),
            user=_env("POSTGRES_USER", "clawsum"),
            password=_env("POSTGRES_PASSWORD", ""),
            dbname=_env("POSTGRES_DB", "clawsum"),
        )
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT processing_status, count(*) AS n
                    FROM ops.emails
                    WHERE mailbox IS NULL OR mailbox = %s
                    GROUP BY 1
                    """,
                    (mailbox,),
                )
                by_status = {r["processing_status"]: int(r["n"]) for r in cur.fetchall()}
                cur.execute(
                    """
                    SELECT COALESCE(review_status, 'unreviewed') AS review_status, count(*) AS n
                    FROM ops.emails
                    WHERE mailbox IS NULL OR mailbox = %s
                    GROUP BY 1
                    """,
                    (mailbox,),
                )
                by_review = {r["review_status"]: int(r["n"]) for r in cur.fetchall()}
                cur.execute(
                    """
                    SELECT count(*) AS n FROM ops.emails
                    WHERE (mailbox IS NULL OR mailbox = %s) AND COALESCE(is_inbox, true)
                    """,
                    (mailbox,),
                )
                inbox_total = int(cur.fetchone()["n"])

                where = [
                    "(e.mailbox IS NULL OR e.mailbox = %s)",
                ]
                params: list[Any] = [mailbox]
                if view == "needs_boss":
                    where.append("e.review_status = 'needs_boss'")
                elif view == "action":
                    where.append(
                        "(e.review_status = 'needs_boss' OR e.processing_status IN ('pending', 'action_required'))"
                    )
                elif view == "inbox":
                    where.append("COALESCE(e.is_inbox, true)")
                else:
                    # default: anything reviewed / actioned / analyzed, else all inbox
                    where.append(
                        """(
                          e.review_status IN ('needs_boss', 'reviewed', 'ignored')
                          OR e.processing_status IN ('pending', 'action_required')
                          OR e.analysis_report IS NOT NULL
                          OR COALESCE(e.is_inbox, true)
                        )"""
                    )
                where_sql = " AND ".join(where)

                cur.execute(
                    f"SELECT count(*) AS n FROM ops.emails e WHERE {where_sql}",
                    tuple(params),
                )
                match_total = int(cur.fetchone()["n"])

                cur.execute(
                    f"""
                    SELECT e.id, e.subject, e.from_addr, e.to_addrs, e.snippet, e.body_text,
                           e.processing_status, e.review_status, e.review_notes,
                           e.paperclip_issue_id, e.received_at, e.is_inbox, e.labels,
                           e.analysis_summary, e.analysis_intent, e.analysis_recommendation,
                           e.analysis_priority, e.analysis_report, e.analysis_json, e.gmail_id,
                           b.slug AS business_slug, b.name AS business_name,
                           p.display_name AS person_name, p.primary_email AS person_email,
                           r.questions AS review_questions, r.signals AS review_signals,
                           r.report_markdown AS review_report, r.priority AS review_priority,
                           r.action_required, r.is_noise, r.analyzed_at
                    FROM ops.emails e
                    LEFT JOIN ops.businesses b ON b.id = e.business_id
                    LEFT JOIN ops.people p ON p.id = e.person_id
                    LEFT JOIN LATERAL (
                      SELECT questions, signals, report_markdown, priority,
                             action_required, is_noise, analyzed_at
                      FROM ops.email_reviews er
                      WHERE er.email_id = e.id OR er.gmail_id = e.gmail_id
                      ORDER BY er.analyzed_at DESC NULLS LAST
                      LIMIT 1
                    ) r ON true
                    WHERE {where_sql}
                    ORDER BY
                      CASE COALESCE(e.analysis_priority, r.priority)
                        WHEN 'urgent' THEN 0 WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2 WHEN 'low' THEN 3
                        ELSE 4
                      END,
                      e.received_at DESC NULLS LAST
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params + [limit, offset]),
                )
                items = [dict(r) for r in cur.fetchall()]
                for it in items:
                    if it.get("received_at") is not None:
                        it["received_at"] = it["received_at"].isoformat()
                    if it.get("analyzed_at") is not None:
                        it["analyzed_at"] = it["analyzed_at"].isoformat()
                    # Prefer longer narrative
                    if not it.get("analysis_report") and it.get("review_report"):
                        it["analysis_report"] = it["review_report"]
                    # Serialize JSON-ish
                    if it.get("analysis_json") is not None and not isinstance(it["analysis_json"], (dict, list)):
                        try:
                            it["analysis_json"] = json.loads(it["analysis_json"])
                        except Exception:
                            pass
                    for list_key in ("to_addrs", "labels", "review_questions", "review_signals"):
                        if it.get(list_key) is not None and not isinstance(it[list_key], list):
                            try:
                                it[list_key] = list(it[list_key])
                            except Exception:
                                it[list_key] = []

                cur.execute(
                    """
                    SELECT count(*) AS n FROM ops.reminders
                    WHERE completed_at IS NULL
                      AND (snoozed_until IS NULL OR snoozed_until < CURRENT_DATE)
                    """
                )
                reminders_active = int(cur.fetchone()["n"])
                cur.execute(
                    """
                    SELECT count(*) AS n FROM ops.email_reviews
                    WHERE mailbox = %s OR mailbox IS NULL
                    """,
                    (mailbox,),
                )
                reviews_stored = int(cur.fetchone()["n"])

                cur.execute(
                    """
                    SELECT t.id, t.title, t.status, t.priority, t.source, t.description,
                           t.created_at, t.due_at, b.slug AS business_slug,
                           e.subject AS email_subject, e.gmail_id
                    FROM ops.tasks t
                    LEFT JOIN ops.businesses b ON b.id = t.business_id
                    LEFT JOIN ops.emails e ON e.id = t.email_id
                    WHERE t.completed_at IS NULL
                    ORDER BY
                      CASE t.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2 ELSE 3 END,
                      t.created_at DESC NULLS LAST
                    LIMIT 200
                    """
                )
                open_tasks = [dict(r) for r in cur.fetchall()]
                for t in open_tasks:
                    if t.get("created_at") is not None:
                        t["created_at"] = t["created_at"].isoformat()
                    if t.get("due_at") is not None:
                        t["due_at"] = t["due_at"].isoformat()
        conn.close()
        questions = []
        for it in items:
            rq = it.get("review_questions") or []
            if rq:
                for q in rq[:3]:
                    if q and q not in questions:
                        questions.append(str(q))
            elif it.get("review_status") == "needs_boss" or it.get("processing_status") == "action_required":
                questions.append(
                    f"Email: {(it.get('subject') or '')[:70]} — outcome / Paperclip link?"
                )
            if len(questions) >= 30:
                break
        action_items = [
            i
            for i in items
            if i.get("review_status") == "needs_boss"
            or i.get("processing_status") in ("pending", "action_required")
            or i.get("action_required")
        ]
        return JSONResponse(
            {
                "ok": True,
                "mailbox": mailbox,
                "view": view,
                "limit": limit,
                "offset": offset,
                "match_total": match_total,
                "inbox_total": inbox_total,
                "has_more": offset + len(items) < match_total,
                "by_status": by_status,
                "by_review": by_review,
                "action_items": action_items,
                "email_analyses": items,
                "open_tasks": open_tasks,
                "reviews_stored": reviews_stored,
                "reminders_active": reminders_active,
                "questions_for_boss": questions,
                "clawsum_instructions": [
                    "Expand each item for full original body + deep narrative.",
                    "Reconcile against cell/person; propose Paperclip tasks for needs_boss.",
                    "Inbox reviews are ChatGPT-style (opinion + project fit). Re-run gmail-inbox-review.py for new mail.",
                ],
            }
        )
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "mailbox": mailbox,
                "action_items": [],
                "email_analyses": [],
                "open_tasks": [],
                "error": str(exc),
                "hint": "Apply 05-ops-email.sql + 14-ops-crm.sql; run gmail-sync + gmail-inbox-review",
            }
        )


@router.get("/crm")
def crm() -> JSONResponse:
    """Cells / people / places / local tasks counts."""
    try:
        import psycopg2
        import psycopg2.extras  # type: ignore

        conn = psycopg2.connect(
            host=_env("POSTGRES_HOST", "127.0.0.1"),
            port=int(_env("POSTGRES_PORT", "5432") or "5432"),
            user=_env("POSTGRES_USER", "clawsum"),
            password=_env("POSTGRES_PASSWORD", ""),
            dbname=_env("POSTGRES_DB", "clawsum"),
        )
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT slug, name, type FROM ops.businesses WHERE active ORDER BY slug"
                )
                cells = [dict(r) for r in cur.fetchall()]
                cur.execute(
                    """
                    SELECT display_name, kind, primary_email, company_name
                    FROM ops.people WHERE active
                    ORDER BY kind, display_name LIMIT 50
                    """
                )
                people = [dict(r) for r in cur.fetchall()]
                cur.execute(
                    "SELECT name, kind, city, region FROM ops.places WHERE active ORDER BY name"
                )
                places = [dict(r) for r in cur.fetchall()]
                cur.execute(
                    """
                    SELECT t.title, t.status, t.priority, b.slug AS business_slug
                    FROM ops.tasks t
                    LEFT JOIN ops.businesses b ON b.id = t.business_id
                    WHERE t.completed_at IS NULL
                    ORDER BY
                      CASE t.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2 ELSE 3 END,
                      t.created_at DESC
                    LIMIT 25
                    """
                )
                tasks = [dict(r) for r in cur.fetchall()]
        conn.close()
        return JSONResponse(
            {
                "ok": True,
                "cells": cells,
                "people": people,
                "places": places,
                "open_tasks": tasks,
            }
        )
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "cells": [],
                "people": [],
                "places": [],
                "open_tasks": [],
                "error": str(exc),
                "hint": "Apply 14-ops-crm.sql; run seed-business-cells + seed-people-places",
            }
        )


@router.get("/approvals")
def approvals(limit: int = 25) -> JSONResponse:
    limit = max(1, min(limit, 100))
    try:
        import psycopg2
        import psycopg2.extras  # type: ignore

        conn = psycopg2.connect(
            host=_env("POSTGRES_HOST", "127.0.0.1"),
            port=int(_env("POSTGRES_PORT", "5432") or "5432"),
            user=_env("POSTGRES_USER", "clawsum"),
            password=_env("POSTGRES_PASSWORD", ""),
            dbname=_env("POSTGRES_DB", "clawsum"),
        )
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT a.id, a.action_type, a.action_summary, a.risk_level,
                           a.status, a.agent_name, a.created_at, b.slug AS business_slug,
                           b.name AS business_name
                    FROM ops.approvals a
                    LEFT JOIN ops.businesses b ON b.id = a.business_id
                    ORDER BY a.created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        for r in rows:
            if r.get("id") is not None:
                r["id"] = str(r["id"])
            if r.get("created_at") is not None:
                r["created_at"] = r["created_at"].isoformat()
        return JSONResponse({"ok": True, "approvals": rows})
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "approvals": [],
                "error": str(exc),
                "hint": "Apply postgres-init/12-overwatch.sql and seed-business-cells.py",
            }
        )


def _openclaw_config() -> tuple[dict[str, Any], str]:
    candidates = [
        Path("/docker/clawsum/data/.openclaw/openclaw.json"),
        Path("/home/node/.openclaw/openclaw.json"),
        Path("/docker/clawsum/openclaw.json"),
    ]
    for p in candidates:
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data, str(p)
            except Exception:
                continue
    return {}, ""


def _channel_row(name: str, enabled: bool | None, detail: str, href: str = "") -> dict[str, Any]:
    if enabled is True:
        status = "live"
    elif enabled is False:
        status = "disabled"
    else:
        status = "unknown"
    return {"id": name, "name": name.title(), "enabled": bool(enabled), "status": status, "detail": detail, "href": href}


@router.get("/channels")
def live_channels() -> JSONResponse:
    """Live Discord / Telegram / gateway status — not the stale Hermes toggle page."""
    cfg, path = _openclaw_config()
    channels = cfg.get("channels") if isinstance(cfg.get("channels"), dict) else {}
    plugins = cfg.get("plugins") if isinstance(cfg.get("plugins"), dict) else {}
    rows = []
    for key in ("discord", "telegram", "whatsapp", "slack"):
        ch = channels.get(key) if isinstance(channels.get(key), dict) else {}
        plug = plugins.get(key) if isinstance(plugins.get(key), dict) else {}
        enabled = ch.get("enabled")
        if enabled is None:
            enabled = plug.get("enabled")
        token_env = {
            "discord": "DISCORD_BOT_TOKEN",
            "telegram": "TELEGRAM_BOT_TOKEN",
            "whatsapp": "WHATSAPP_TOKEN",
            "slack": "SLACK_BOT_TOKEN",
        }.get(key, "")
        has_token = bool(_env(token_env)) if token_env else False
        if enabled is None and has_token:
            enabled = True
        detail = "config present" if ch or plug else "not in openclaw.json"
        if has_token:
            detail += " · token set"
        if key == "discord":
            href = "https://openclaw.clawsum.com"
            desk = _env("DISCORD_BOSS_DESK_CHANNEL_ID")
            if desk:
                detail += " · Boss Desk bound"
        elif key == "telegram":
            href = "https://openclaw.clawsum.com"
        else:
            href = "https://openclaw.clawsum.com"
        rows.append(_channel_row(key, enabled if isinstance(enabled, bool) else None, detail, href))
    gw = _http_json(_env("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:48166") + "/healthz", timeout=3.0)
    return JSONResponse(
        {
            "ok": True,
            "source": path or "env",
            "gateway_up": gw is not None,
            "channels": rows,
            "note": "Hermes Channels page can show disabled when it reads a different config. This feed is OpenClaw live.",
        }
    )


def _expected_cron() -> list[dict[str, Any]]:
    return [
        {"id": "daily-brief", "name": "Morning Boss brief", "schedule": "07:30 Chicago", "marker": "run-daily-global-report.sh", "href": "/home?tab=brief"},
        {"id": "agent-review", "name": "Agent daily reviews", "schedule": "with morning brief", "marker": "daily-agent-review.py", "href": "/home?tab=brief"},
        {"id": "gmail-sync", "name": "Gmail sync", "schedule": "every 15m", "marker": "gmail-sync.py", "href": "/inbox"},
        {"id": "gmail-review", "name": "Gmail inbox review", "schedule": "every 15m", "marker": "gmail-inbox-review", "href": "/inbox"},
        {"id": "gmail-triage", "name": "Gmail triage", "schedule": ":17/:47", "marker": "gmail-triage.py", "href": "/inbox"},
        {"id": "memory-dream", "name": "Night memory dream", "schedule": "Chicago night window", "marker": "run-memory-dream.sh", "href": "/home?tab=archive"},
        {"id": "archive-obsidian", "name": "Archive → Obsidian", "schedule": "hourly :40", "marker": "poll-archive-to-obsidian.py", "href": "/home?tab=graph"},
        {"id": "obsidian-sync", "name": "Obsidian report sync", "schedule": "every 15m", "marker": "sync-obsidian-reports.sh", "href": "/home?tab=graph"},
        {"id": "reminders", "name": "Boss reminders", "schedule": "daily", "marker": "reminders-notify.py", "href": "/inbox"},
        {"id": "ghl-weekly", "name": "GHL weekly REI", "schedule": "Mon 08:00", "marker": "ghl-weekly-report.py", "href": "/agents"},
        {"id": "outage-watch", "name": "Chat outage watch", "schedule": "frequent", "marker": "chat-outage-watch.py", "href": "/home?tab=channels"},
    ]


@router.get("/cron")
def live_cron() -> JSONResponse:
    """Clawsum scheduled jobs — host crontab dump + expected catalog."""
    live_txt = Path("/docker/clawsum/data/reports/cron-live.txt")
    registry = Path("/docker/clawsum/data/reports/cron-registry.json")
    dumped = ""
    if live_txt.is_file():
        dumped = live_txt.read_text(encoding="utf-8", errors="replace")
    expected = _expected_cron()
    if registry.is_file():
        try:
            extra = json.loads(registry.read_text(encoding="utf-8"))
            if isinstance(extra, list):
                expected = extra
            elif isinstance(extra, dict) and isinstance(extra.get("jobs"), list):
                expected = extra["jobs"]
        except Exception:
            pass
    jobs = []
    for job in expected:
        if not isinstance(job, dict):
            continue
        marker = str(job.get("marker") or job.get("id") or "")
        present = bool(marker) and marker in dumped if dumped else None
        row = dict(job)
        row["present"] = present
        row["status"] = "live" if present else ("unknown" if dumped == "" else "missing")
        jobs.append(row)
    live_lines = [ln for ln in dumped.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    return JSONResponse(
        {
            "ok": True,
            "count": len(jobs),
            "live_line_count": len(live_lines),
            "jobs": jobs,
            "note": "Hermes Cron page is Hermes-internal jobs. This list is Clawsum host cron.",
            "refreshed_from": str(live_txt) if dumped else None,
        }
    )


@router.get("/hud")
def hud() -> JSONResponse:
    """Marquee + gauge payload for the jet-cockpit Start screen."""
    auth = _load_authority()
    ch = live_channels().body
    cr = live_cron().body
    try:
        channels = json.loads(ch.decode() if isinstance(ch, (bytes, bytearray)) else ch)
    except Exception:
        channels = {}
    try:
        cron = json.loads(cr.decode() if isinstance(cr, (bytes, bytearray)) else cr)
    except Exception:
        cron = {}
    inbox_need = 0
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=_env("POSTGRES_HOST", "127.0.0.1"),
            port=int(_env("POSTGRES_PORT", "5432") or "5432"),
            user=_env("POSTGRES_USER", "clawsum"),
            password=_env("POSTGRES_PASSWORD", ""),
            dbname=_env("POSTGRES_DB", "clawsum"),
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM ops.emails WHERE review_status = 'needs_boss'"
                )
                inbox_need = int(cur.fetchone()[0] or 0)
        conn.close()
    except Exception:
        pass
    live_ch = [
        c.get("name")
        for c in (channels.get("channels") or [])
        if isinstance(c, dict) and c.get("enabled")
    ]
    ticker = [
        f"CLAWSUM // CEO COCKPIT",
        f"{auth.get('agent_count') or len(auth.get('agents') or [])} agents · {auth.get('skill_count') or len(auth.get('skills') or [])} skills",
        f"Inbox needs Boss: {inbox_need}",
        f"Channels live: {', '.join(live_ch) or 'checking…'}",
        f"Cron jobs tracked: {cron.get('count') or 0}",
        "Say escalate anytime to force the frontier model",
        "Tiles are live links — tap a gauge to open the system",
    ]
    briefs_path = Path("/docker/clawsum/data/reports/agent-daily-briefs.json")
    hermes_alerts: list[str] = []
    if briefs_path.is_file():
        try:
            payload = json.loads(briefs_path.read_text(encoding="utf-8"))
            hermes_alerts = [str(a) for a in (payload.get("hermes_alerts") or [])[:4]]
            ticker.extend(hermes_alerts)
        except Exception:
            pass
    return JSONResponse(
        {
            "ok": True,
            "ticker": ticker,
            "inbox_needs_boss": inbox_need,
            "agent_count": auth.get("agent_count") or len(auth.get("agents") or []),
            "skill_count": auth.get("skill_count") or len(auth.get("skills") or []),
            "channels_live": live_ch,
            "cron_count": cron.get("count") or 0,
            "hermes_alerts": hermes_alerts,
        }
    )


_TOPIC_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("RE", ("avenou", "real estate", "wholesale", "comp", "property", "listing", "seller", "buyer", "rei", "deal")),
    ("GHL", ("ghl", "gohighlevel", "pipeline", "appointment", "crm", "lead")),
    ("Media", ("content", "video", "youtube", "repurpos", "studio", "script", "flyer")),
    ("Legal", ("legal", "llc", "attorney", "compliance")),
    ("Finance", ("bookkeep", "invoice", "revenue", "receivable", "quickbooks", "a/r")),
    ("Growth", ("seo", "ppc", "ads", "funnel", "aeo", "geo")),
    ("Inbox", ("gmail", "email", "oauth", "inbox", "mailbox")),
    ("Platform", ("clawsum", "hermes", "openclaw", "paperclip", "jarvis", "grafana", "vps", "docker")),
    ("Ops", ("cron", "monitor", "alert", "backup", "health")),
]
_AGENT_TOPIC = {
    "realestate": "RE",
    "ghl": "GHL",
    "comms": "Media",
    "research": "Growth",
    "planning": "Ops",
    "coding": "Platform",
    "data": "Ops",
    "admin": "Platform",
    "hermes": "Platform",
    "paperclip": "Platform",
}


def _entity_ok(label: str) -> bool:
    """Keep map nodes as short entities, not sentence-blobs."""
    s = (label or "").strip()
    if not s or s.lower() in {"unknown", "none", "n/a", "null"}:
        return False
    if len(s) > 48 or s.count(" ") > 6:
        return False
    return True


def _topic_of(label: str, source_agent: str = "", fact_type: str = "") -> str:
    blob = f"{label} {source_agent} {fact_type}".lower()
    aid = (source_agent or "").strip().lower()
    if aid in _AGENT_TOPIC:
        return _AGENT_TOPIC[aid]
    for topic, keys in _TOPIC_RULES:
        if any(k in blob for k in keys):
            return topic
    if (fact_type or "").lower() == "project":
        return "Projects"
    return "General"


def _graphify_build(
    rows: list[dict[str, Any]], *, entities_only: bool = False
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    facts_by: dict[str, list[dict[str, Any]]] = {}

    def nid(label: str) -> str | None:
        key = (label or "").strip()[:80] or "unknown"
        if entities_only and not _entity_ok(key):
            return None
        if key not in seen:
            seen[key] = f"n{len(seen)}"
            nodes.append({"id": seen[key], "label": key, "facts": []})
        return seen[key]

    for r in rows:
        a = nid(str(r.get("subject") or ""))
        b = nid(str(r.get("object") or ""))
        if not a or not b or a == b:
            continue
        pred = str(r.get("predicate") or "related")
        edge = {
            "source": a,
            "target": b,
            "label": pred,
            "importance": r.get("importance"),
            "kind": r.get("source_kind"),
        }
        edges.append(edge)
        facts_by.setdefault(a, []).append(
            {"predicate": pred, "other": str(r.get("object") or ""), "dir": "out", "importance": r.get("importance")}
        )
        facts_by.setdefault(b, []).append(
            {"predicate": pred, "other": str(r.get("subject") or ""), "dir": "in", "importance": r.get("importance")}
        )
    for n in nodes:
        n["facts"] = (facts_by.get(n["id"]) or [])[:12]
        n["degree"] = len(facts_by.get(n["id"]) or [])
    return nodes, edges


@router.get("/ops-kpis")
def ops_kpis() -> JSONResponse:
    """Pipeline + project KPIs. Missing SoR stays null — never invented."""
    items = [
        {"id": "leads", "label": "New leads", "value": None, "source": "none"},
        {"id": "appts", "label": "New appointments", "value": None, "source": "none"},
        {"id": "proposals", "label": "Proposals sent", "value": None, "source": "none"},
        {"id": "signed", "label": "Contracts signed", "value": None, "source": "none"},
        {"id": "assigned", "label": "Contracts assigned", "value": None, "source": "none"},
        {"id": "closed", "label": "Contracts closed", "value": None, "source": "none"},
        {"id": "revenue", "label": "Accounts received", "value": None, "source": "none"},
        {"id": "ar", "label": "A/R", "value": None, "source": "none"},
        {"id": "proj_active", "label": "Projects active", "value": None, "source": "none"},
        {"id": "proj_dev", "label": "Projects in dev", "value": None, "source": "none"},
        {"id": "progress", "label": "Progress %", "value": None, "source": "none"},
    ]
    by = {i["id"]: i for i in items}
    try:
        conn = _pg_connect()
        with conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        SELECT count(*) FILTER (WHERE created_at > now() - interval '7 days'),
                               count(*)
                        FROM ops.people
                        WHERE active AND kind = 'lead'
                        """
                    )
                    new_leads, all_leads = cur.fetchone()
                    if all_leads:
                        by["leads"]["value"] = int(new_leads or 0)
                        by["leads"]["source"] = "ops.people kind=lead /7d"
                except Exception:
                    pass
                cur.execute("SELECT count(*) FROM ops.businesses WHERE active")
                by["proj_active"]["value"] = int(cur.fetchone()[0] or 0)
                by["proj_active"]["source"] = "ops.businesses"
                try:
                    cur.execute(
                        """
                        SELECT count(*) FILTER (WHERE fact_type = 'project'),
                               count(*) FILTER (WHERE fact_type = 'task')
                        FROM ops.memory_facts
                        WHERE status = 'active' AND scope <> 'personal'
                        """
                    )
                    proj_f, task_f = cur.fetchone()
                    if not by["proj_active"]["value"] and proj_f:
                        by["proj_active"]["value"] = int(proj_f or 0)
                        by["proj_active"]["source"] = "memory_facts.project"
                    by["proj_dev"]["value"] = int(task_f or 0)
                    by["proj_dev"]["source"] = "memory_facts.task"
                except Exception:
                    pass
        conn.close()
    except Exception:
        pass
    try:
        tasks, _err = _paperclip_issue_list()
        todo = sum(1 for t in tasks if str(t.get("status") or "") in {"todo", "backlog", "open"})
        run = sum(1 for t in tasks if str(t.get("status") or "") in {"in_progress", "in-progress"})
        done = sum(1 for t in tasks if str(t.get("status") or "") in {"done", "complete"})
        if run or todo:
            by["proj_active"]["value"] = run
            by["proj_active"]["source"] = "paperclip in_progress"
            by["proj_dev"]["value"] = todo
            by["proj_dev"]["source"] = "paperclip todo"
        total = todo + run + done
        if total:
            by["progress"]["value"] = int(round(100 * done / total))
            by["progress"]["source"] = "paperclip done/total"
    except Exception:
        pass
    ln = links()
    return JSONResponse(
        {
            "ok": True,
            "kpis": items,
            "grafana": {
                "home": ln.get("grafana"),
                "ops": ln.get("grafana_ops"),
                "health": ln.get("grafana_health"),
                "files": [
                    "deploy/grafana/provisioning/dashboards/json/clawsum-operations.json",
                    "deploy/grafana/provisioning/dashboards/json/clawsum-health.json",
                ],
            },
            "note": "Leads/contracts/revenue need GHL or books SoR. Grafana is infra/ops (https://grafana.clawsum.com).",
        }
    )


@router.get("/graphify")
def graphify(limit: int = 64, q: str = "", mode: str = "map", cluster: str = "") -> JSONResponse:
    """Triple graph payload: Hermes clusters + Arcade mirror + Obsidian notes."""
    import sys

    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    from graphify_views import arcade_status, clustered_hermes, obsidian_graph

    limit = max(16, min(int(limit or 64), 200))
    needle = (q or "").strip()[:80]
    cluster = (cluster or "").strip()[:40]
    try:
        import psycopg2.extras

        conn = _pg_connect()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT count(*)::int AS n
                    FROM ops.memory_facts
                    WHERE status = 'active' AND scope <> 'personal'
                    """
                )
                total_facts = int((cur.fetchone() or {}).get("n") or 0)
                if needle:
                    cur.execute(
                        """
                        SELECT id::text, subject, predicate, object, importance, source_kind,
                               COALESCE(source_agent, '') AS source_agent,
                               COALESCE(fact_type, 'observation') AS fact_type
                        FROM ops.memory_facts
                        WHERE status = 'active' AND scope <> 'personal'
                          AND (subject ILIKE %s OR object ILIKE %s OR predicate ILIKE %s)
                        ORDER BY
                          CASE importance
                            WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                            WHEN 'medium' THEN 2 ELSE 3
                          END,
                          updated_at DESC NULLS LAST
                        LIMIT %s
                        """,
                        (f"%{needle}%", f"%{needle}%", f"%{needle}%", limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id::text, subject, predicate, object, importance, source_kind,
                               COALESCE(source_agent, '') AS source_agent,
                               COALESCE(fact_type, 'observation') AS fact_type
                        FROM ops.memory_facts
                        WHERE status = 'active' AND scope <> 'personal'
                        ORDER BY
                          CASE importance
                            WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                            WHEN 'medium' THEN 2 ELSE 3
                          END,
                          updated_at DESC NULLS LAST
                        LIMIT %s
                        """,
                        (max(limit * 8, 400),),
                    )
                rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        nodes, edges, clusters = clustered_hermes(rows, cluster=cluster)
        arcade = arcade_status(_env)
        arcade["nodes"] = [
            {"id": n["id"], "label": n["label"], "kind": n.get("kind") or "entity"}
            for n in nodes
        ][:72]
        arcade["edges"] = edges[:140]
        obsidian = obsidian_graph(72)
        kpis = json.loads(ops_kpis().body.decode())
        return JSONResponse(
            {
                "ok": True,
                "nodes": nodes,
                "edges": edges,
                "clusters": clusters,
                "count": len(rows),
                "total_facts": total_facts,
                "q": needle or None,
                "cluster": cluster or None,
                "mode": "cluster",
                "engine": "graphify",
                "arcade": arcade,
                "obsidian": obsidian,
                "kpis": kpis.get("kpis") or [],
                "grafana": kpis.get("grafana") or {},
                "arcade_studio": "http://127.0.0.1:2480",
                "arcade_note": arcade.get("note") or "",
            }
        )
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "nodes": [],
                "edges": [],
                "error": str(exc),
                "hint": "Apply 19-ops-memory-graph.sql and run poll-archive-to-obsidian / memory extract.",
            }
        )


@router.get("/agent-briefs")
def agent_briefs() -> JSONResponse:
    path = Path("/docker/clawsum/data/reports/agent-daily-briefs.json")
    if not path.is_file():
        return JSONResponse({"ok": True, "briefs": [], "hermes_alerts": [], "note": "Run daily-agent-review.py"})
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["ok"] = True
        return JSONResponse(data)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc), "briefs": []})


@router.post("/inbox/reply")
async def inbox_reply(request: Request) -> JSONResponse:
    """Boss answers an Ask Boss question directly from the cockpit."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    question = str(body.get("question") or "").strip()
    reply = str(body.get("reply") or "").strip()
    email_id = str(body.get("email_id") or "").strip()
    if not question or not reply:
        return JSONResponse({"ok": False, "error": "question and reply required"}, status_code=400)
    stored = False
    store_err = ""
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=_env("POSTGRES_HOST", "127.0.0.1"),
            port=int(_env("POSTGRES_PORT", "5432") or "5432"),
            user=_env("POSTGRES_USER", "clawsum"),
            password=_env("POSTGRES_PASSWORD", ""),
            dbname=_env("POSTGRES_DB", "clawsum"),
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ops.boss_replies (
                      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                      email_id TEXT,
                      question TEXT NOT NULL,
                      reply TEXT NOT NULL,
                      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
                cur.execute(
                    """
                    INSERT INTO ops.boss_replies (email_id, question, reply)
                    VALUES (%s, %s, %s)
                    """,
                    (email_id or None, question[:2000], reply[:8000]),
                )
                if email_id:
                    try:
                        cur.execute(
                            """
                            UPDATE ops.emails
                            SET review_notes = trim(both from concat_ws(E'\\n', review_notes, %s)),
                                review_status = 'reviewed'
                            WHERE id::text = %s OR gmail_id = %s
                            """,
                            (f"BOSS: {reply[:1500]}", email_id, email_id),
                        )
                    except Exception:
                        pass
        conn.close()
        stored = True
    except Exception as exc:
        store_err = str(exc)
        log = Path("/docker/clawsum/data/reports/boss-replies.jsonl")
        try:
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "question": question,
                            "reply": reply,
                            "email_id": email_id,
                        }
                    )
                    + "\n"
                )
            stored = True
        except Exception as exc2:
            store_err = f"{store_err}; file:{exc2}"
    return JSONResponse(
        {
            "ok": stored,
            "stored": stored,
            "error": store_err or None,
            "chat_hint": f"Boss replied to: {question[:120]}",
            "next": "Jarvis will treat this as an answered Ask Boss item on the next review.",
        }
    )


@router.get("/kanban")
def kanban() -> JSONResponse:
    """Live Paperclip columns — replaces empty Hermes kanban.db."""
    statuses = (
        ("blocked", "Blocked", "rose"),
        ("in_progress", "In progress", "cyan"),
        ("todo", "Todo", "amber"),
        ("backlog", "Backlog", "violet"),
        ("done", "Done", "lime"),
    )
    api = _paperclip_api()
    company = _paperclip_company_id()
    board = (links() or {}).get("paperclip") or "https://paperclip.clawsum.com"
    columns: list[dict[str, Any]] = []
    err = ""
    total = 0
    if not company:
        err = "Paperclip company not resolved"
    for sid, label, tone in statuses:
        cards: list[dict[str, Any]] = []
        if company:
            raw = _http_json(f"{api}/companies/{company}/issues?status={sid}&limit=40")
            items = raw if isinstance(raw, list) else (
                (raw or {}).get("issues") or (raw or {}).get("items") or []
                if isinstance(raw, dict)
                else []
            )
            if raw is None and not err:
                err = f"Paperclip unreachable ({sid})"
            for it in items:
                if not isinstance(it, dict):
                    continue
                ident = it.get("identifier") or it.get("key") or it.get("id") or ""
                title = it.get("title") or it.get("name") or str(ident) or "Untitled"
                cards.append(
                    {
                        "id": str(ident or title),
                        "title": f"{ident} {title}".strip() if ident else str(title),
                        "assignee": it.get("assigneeName") or it.get("assignee") or it.get("agent") or "",
                        "status": sid,
                        "href": f"{board.rstrip('/')}/issues/{it.get('id') or ident}" if (it.get("id") or ident) else board,
                    }
                )
        if sid != "done":
            total += len(cards)
        columns.append({"id": sid, "label": label, "tone": tone, "cards": cards[:30]})
    return JSONResponse(
        {
            "ok": not err,
            "error": err or None,
            "total": total,
            "columns": columns,
            "links": links(),
        }
    )


@router.get("/vendor/{name}")
def vendor_asset(name: str) -> FileResponse:
    safe = Path(name).name
    allowed = {"three.min.js", "3d-force-graph.min.js"}
    if safe not in allowed:
        raise HTTPException(status_code=404, detail="not found")
    roots = [
        Path(__file__).resolve().parent / "dist" / "vendor",
        Path("/paperclip/.hermes/plugins/clawsum-cockpit/dashboard/dist/vendor"),
        Path("/docker/clawsum/examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/dist/vendor"),
    ]
    for root in roots:
        path = root / safe
        if path.is_file():
            return FileResponse(path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="vendor missing")


@router.get("/assets/{name}")
def asset(name: str) -> FileResponse:
    safe = Path(name).name
    path = _assets_dir() / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail="not found")
    media = "image/svg+xml" if safe.endswith(".svg") else "application/octet-stream"
    return FileResponse(path, media_type=media)
