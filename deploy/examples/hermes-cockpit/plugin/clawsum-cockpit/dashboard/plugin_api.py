"""
Clawsum cockpit backend — FastAPI router for Hermes dashboard plugin.

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
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter()


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


def _env(key: str, default: str = "") -> str:
    return (os.environ.get(key) or default).strip()


def _http_json(url: str, timeout: float = 4.0) -> Any | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "plugin": "clawsum-cockpit"}


@router.get("/links")
def links() -> dict[str, str]:
    return {
        "boss": _env("CLAWSUM_BOSS_URL", _env("PAPERCLIP_PUBLIC_URL", "http://127.0.0.1:3100")),
        "openclaw": _env("CLAWSUM_OPENCLAW_URL", "https://clawsum.srv.example.com"),
        "grafana": _env("CLAWSUM_GRAFANA_URL", "http://127.0.0.1:3000"),
        "grafana_embed": _env(
            "CLAWSUM_GRAFANA_EMBED_URL",
            _env("CLAWSUM_GRAFANA_URL", "http://127.0.0.1:3000"),
        ),
        "hermes": _env("CLAWSUM_HERMES_URL", "http://127.0.0.1:9119"),
    }


@router.get("/brief")
def brief() -> JSONResponse:
    """CEO daily brief payload — Paperclip + approvals when available."""
    api = _env("PAPERCLIP_API", "http://127.0.0.1:3100/api").rstrip("/")
    company = _env("PAPERCLIP_COMPANY_ID")
    tasks: dict[str, Any] = {}
    if company:
        dash = _http_json(f"{api}/companies/{company}/dashboard")
        if isinstance(dash, dict):
            tasks = {
                "agents": dash.get("agents") or dash.get("agentCounts"),
                "issues": dash.get("tasks") or dash.get("issueCounts"),
            }

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
                "paperclip": tasks,
                "links": links(),
            }
        )

    priorities = []
    if approvals_pending:
        priorities.append(f"{approvals_pending} approval(s) waiting in overwatch queue.")
    if not tasks:
        priorities.append("Paperclip dashboard unreachable — check PAPERCLIP_API / company id.")
    if archive_pending:
        priorities.append(
            f"{archive_pending} archive item(s) pending/blocked — ask clarifying questions (Archive tab)."
        )
    if not priorities:
        priorities.append("No urgent overwatch items. Review Hermes chat + Boss backlog.")

    return JSONResponse(
        {
            "ok": True,
            "source": "live",
            "priorities": priorities,
            "pending_approvals": approvals_pending,
            "business_cells": businesses,
            "archive_pending": archive_pending,
            "paperclip": tasks,
            "links": links(),
        }
    )


@router.get("/archive")
def archive(limit: int = 12) -> JSONResponse:
    """Proactive ChatGPT-archive brief for Hermes (questions + drive-forward)."""
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
                    "SELECT count(*) FROM ops.conversations WHERE scope = 'personal'"
                )
                personal_n = int(cur.fetchone()[0])
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
        return JSONResponse(
            {
                "ok": True,
                "priorities": priorities,
                "counts_by_scope_status": counts,
                "personal_conversations": personal_n,
                "drive_forward": drive,
                "questions_for_boss": questions[:8],
                "hermes_instructions": [
                    "Read Paperclip tasks first; link related archive items.",
                    "Ask one sharp question per pending/blocked/unknown item.",
                    "Keep personal scope out of business agents and Hermes memory.",
                ],
            }
        )
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "drive_forward": [],
                "questions_for_boss": [],
                "error": str(exc),
                "hint": "Apply postgres-init/13-chatgpt-archive.sql then import/classify/link",
            }
        )


@router.get("/inbox")
def inbox(limit: int = 20) -> JSONResponse:
    """clawsums@gmail.com review snapshot for Hermes / cockpit."""
    limit = max(1, min(limit, 100))
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
                    SELECT e.subject, e.from_addr, e.processing_status, e.review_status,
                           e.paperclip_issue_id, e.received_at, e.analysis_summary,
                           e.analysis_intent, e.analysis_recommendation, e.analysis_priority,
                           e.analysis_report, e.gmail_id,
                           b.slug AS business_slug,
                           p.display_name AS person_name
                    FROM ops.emails e
                    LEFT JOIN ops.businesses b ON b.id = e.business_id
                    LEFT JOIN ops.people p ON p.id = e.person_id
                    WHERE (e.mailbox IS NULL OR e.mailbox = %s)
                      AND (
                        e.review_status IN ('needs_boss', 'reviewed', 'ignored')
                        OR e.processing_status IN ('pending', 'action_required')
                        OR e.analysis_report IS NOT NULL
                      )
                    ORDER BY
                      CASE e.analysis_priority
                        WHEN 'urgent' THEN 0 WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2 WHEN 'low' THEN 3
                        ELSE 4
                      END,
                      e.received_at DESC NULLS LAST
                    LIMIT %s
                    """,
                    (mailbox, limit),
                )
                items = [dict(r) for r in cur.fetchall()]
                for it in items:
                    if it.get("received_at") is not None:
                        it["received_at"] = it["received_at"].isoformat()
                cur.execute(
                    """
                    SELECT count(*) FROM ops.reminders
                    WHERE completed_at IS NULL
                      AND (snoozed_until IS NULL OR snoozed_until < CURRENT_DATE)
                    """
                )
                reminders_active = int(cur.fetchone()[0])
                cur.execute(
                    """
                    SELECT count(*) FROM ops.email_reviews
                    WHERE mailbox = %s OR mailbox IS NULL
                    """,
                    (mailbox,),
                )
                reviews_stored = int(cur.fetchone()[0])
        conn.close()
        questions = []
        for it in items:
            if it.get("review_status") == "needs_boss" or it.get("processing_status") == "action_required":
                questions.append(
                    f"Email: {(it.get('subject') or '')[:70]} — outcome / Paperclip link?"
                )
            if len(questions) >= 8:
                break
        return JSONResponse(
            {
                "ok": True,
                "mailbox": mailbox,
                "by_status": by_status,
                "by_review": by_review,
                "action_items": [
                    i
                    for i in items
                    if i.get("review_status") == "needs_boss"
                    or i.get("processing_status") in ("pending", "action_required")
                ],
                "email_analyses": items,
                "reviews_stored": reviews_stored,
                "reminders_active": reminders_active,
                "questions_for_boss": questions,
                "hermes_instructions": [
                    "Every inbox email has a stored analysis report — read intent + recommendation.",
                    "Link each to a business cell + person; propose Paperclip tasks for needs_boss.",
                    "Ask one clarifying question per needs_boss item.",
                ],
            }
        )
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "mailbox": mailbox,
                "action_items": [],
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


@router.get("/assets/{name}")
def asset(name: str) -> FileResponse:
    safe = Path(name).name
    path = _assets_dir() / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail="not found")
    media = "image/svg+xml" if safe.endswith(".svg") else "application/octet-stream"
    return FileResponse(path, media_type=media)
