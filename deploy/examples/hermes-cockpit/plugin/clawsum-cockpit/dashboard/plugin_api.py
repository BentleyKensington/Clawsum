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
  DATABASE_URL or POSTGRES_* for ops.approvals
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
                "paperclip": tasks,
                "links": links(),
            }
        )

    priorities = []
    if approvals_pending:
        priorities.append(f"{approvals_pending} approval(s) waiting in overwatch queue.")
    if not tasks:
        priorities.append("Paperclip dashboard unreachable — check PAPERCLIP_API / company id.")
    if not priorities:
        priorities.append("No urgent overwatch items. Review Hermes chat + Boss backlog.")

    return JSONResponse(
        {
            "ok": True,
            "source": "live",
            "priorities": priorities,
            "pending_approvals": approvals_pending,
            "business_cells": businesses,
            "paperclip": tasks,
            "links": links(),
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
