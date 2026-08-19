#!/usr/bin/env python3
"""
Comprehensive weekly GHL REI report for MCO / Avenou (and other REI slugs).

Runs strategic audit (optional), builds Boss-facing weekly ops markdown,
writes Obsidian + workspace WEEKLY.md, notifies Telegram digest / account group.

Usage (VPS):
  python3 /docker/clawsum/scripts/ghl-weekly-report.py --slugs mco-rei,ave-rei
  python3 /docker/clawsum/scripts/ghl-weekly-report.py --slugs mco-rei --no-audit --dry-run
  python3 /docker/clawsum/scripts/ghl-weekly-report.py --slugs ave-rei --audit --use-llm
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl
from ghl_mcp_client import (
    load_env,
    mcp_tool,
    mcp_tools_list,
    psql_as_account,
    sync_db_password,
)

ROOT = Path("/docker/clawsum")
OBS = ROOT / "obsidian"
REPORT_DIR = ROOT / "data" / "reports" / "ghl-weekly"
TZ = ZoneInfo("America/Chicago")
DEFAULT_SLUGS = ("mco-rei", "ave-rei", "dispo-dudes")
DAILY_LIMIT = 10


def parse_slugs(raw: str | None) -> list[str]:
    if not raw or raw.strip().lower() in ("all", "rei", "default"):
        configured = {a["slug"] for a in ghl.accounts()}
        return [s for s in DEFAULT_SLUGS if s in configured] or [
            a["slug"] for a in ghl.accounts() if "rei" in a["slug"]
        ]
    return [s.strip() for s in raw.split(",") if s.strip()]


def run_strategic_audit(slug: str, use_llm: bool) -> int:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "ghl-strategic-audit.py"),
        "--slug",
        slug,
        "--vertical",
        "rei",
    ]
    if use_llm:
        cmd.append("--use-llm")
    print(f"=== Running strategic audit: {' '.join(cmd)} ===")
    return subprocess.call(cmd)


def fetch_pipelines(pit: str, loc: str, available: set[str]) -> list[dict[str, Any]]:
    data = mcp_tool("opportunities_get-pipelines", {}, pit, loc, available)
    if isinstance(data, dict):
        return data.get("pipelines") or []
    return []


def fetch_opportunities(
    pit: str, loc: str, available: set[str], limit: int = 200
) -> list[dict[str, Any]]:
    for tool in (
        "opportunities_search-opportunity",
        "opportunities_get-opportunities",
    ):
        if tool not in available:
            continue
        data = mcp_tool(
            tool,
            {"locationId": loc, "limit": limit, "status": "open"},
            pit,
            loc,
            available,
        )
        if isinstance(data, dict):
            opps = data.get("opportunities") or data.get("data") or []
            if isinstance(opps, list):
                return opps
        if isinstance(data, list):
            return data
    return []


def stage_counts(
    pipelines: list[dict[str, Any]], opps: list[dict[str, Any]]
) -> list[tuple[str, str, int]]:
    """Return (pipeline_name, stage_name, count) sorted by count desc."""
    pipe_by_id: dict[str, str] = {}
    stage_by_id: dict[str, tuple[str, str]] = {}
    for p in pipelines:
        pid = str(p.get("id") or "")
        pname = p.get("name") or pid or "?"
        pipe_by_id[pid] = pname
        for s in p.get("stages") or []:
            sid = str(s.get("id") or "")
            sname = s.get("name") or sid or "?"
            stage_by_id[sid] = (pname, sname)

    counts: dict[tuple[str, str], int] = {}
    for o in opps:
        pid = str(o.get("pipelineId") or o.get("pipeline_id") or "")
        sid = str(o.get("pipelineStageId") or o.get("stageId") or "")
        if sid in stage_by_id:
            key = stage_by_id[sid]
        else:
            pname = pipe_by_id.get(pid) or o.get("pipelineName") or "Unknown pipeline"
            sname = o.get("pipelineStageName") or o.get("stageName") or sid or "?"
            key = (pname, sname)
        counts[key] = counts.get(key, 0) + 1

    rows = [(p, s, n) for (p, s), n in counts.items()]
    rows.sort(key=lambda x: (-x[2], x[0], x[1]))
    return rows


def classify_pipeline(name: str) -> str:
    low = (name or "").lower()
    if any(k in low for k in ("buyer", "dispos", "cash buy", "wholesale buy")):
        return "buyer"
    if any(k in low for k in ("seller", "acquis", "lead", "motivat", "offer")):
        return "seller"
    return "other"


def _human_why(priority: str, kind: str, reason: str) -> str:
    kind = (kind or "").strip()
    reason = (reason or "").strip()
    if kind == "dropped_call":
        return (
            f"{priority.title()} because we were already on the phone, the call dropped, "
            "and they asked to continue later — we never called back. That is a live conversation we abandoned."
        )
    if kind == "warm_intro":
        return (
            f"{priority.title()} because this is a warm handoff (they were told we would call). "
            "Someone already opened the door; if we do not call today the intro goes cold."
        )
    if kind == "missed_call":
        return (
            f"{priority.title()} because they called or we missed them and there was no callback or text-back. "
            "Treat as a live inbound, not a drip."
        )
    if kind == "callback_asked":
        return (
            f"{priority.title()} because they asked us to call or text back and we have not done it."
        )
    if kind == "unanswered_inbound":
        return (
            f"{priority.title()} because they wrote us and nobody closed the loop"
            + (f" ({reason})" if reason else ".")
        )
    return reason or f"{priority.title()} — follow-up gap that still needs a human."


def _human_brief(name: str, kind: str, hook: str, reason: str, action: str) -> str:
    first = (name or "This contact").strip().split()[0].title()
    hook = (hook or "").strip()
    if kind == "dropped_call":
        story = (
            f"{first} was already talking with us; the call failed and they said to continue later. "
            "They deserve attention because this is not a cold lead — we left them hanging mid-conversation."
        )
    elif kind == "warm_intro":
        story = (
            f"{first} was told to expect our call. We never finished a real conversation. "
            "Worth your time because the trust was borrowed from whoever referred them."
        )
    elif kind == "missed_call":
        story = (
            f"{first} called or we missed them. No callback yet. "
            "A same-day call or text-back is the whole job here."
        )
    elif hook and "http" not in hook.lower() and "msgsndr" not in hook.lower():
        story = (
            f"{first}: {hook}. {reason or 'There is an open loop.'} "
            "Follow up because we have something specific to reference — not a generic blast."
        )
    else:
        story = (
            f"{first} is on the list because {reason or 'there is an unanswered inbound'}. "
            "Qualify motivation and timeline on the call."
        )
    if action:
        story += f" Next: {action}"
    return story


def _csv_lead_row(rec: dict[str, str]) -> dict[str, Any]:
    pri = rec.get("priority") or "?"
    kind = rec.get("situation_kind") or ""
    reason = rec.get("reason") or ""
    name = rec.get("contact_name") or "?"
    hook = rec.get("contact_specific_hook") or ""
    why = (rec.get("priority_why") or "").strip()
    weak_why = (
        not why
        or why.lower() in ("high", "critical", "medium", "low")
        or why.lower().startswith("high priority")
        or why.lower().startswith("medium priority")
        or why.lower().startswith("critical priority")
    )
    if weak_why:
        why = _human_why(pri, kind, reason)
    brief = (rec.get("boss_brief") or "").strip()
    weak_brief = (
        not brief
        or "keep momentum" in brief.lower()
        or "deserves follow-up" in brief.lower()
        or "warrants follow-up" in brief.lower()
        or "needs her attention" in brief.lower()
        or "needs engagement" in brief.lower()
        or len(brief) < 60
    )
    if weak_brief:
        brief = _human_brief(name, kind, hook, reason, rec.get("suggested_action") or "")
    return {
        "contact_id": rec.get("contact_id") or "",
        "priority": pri,
        "name": name,
        "phone": rec.get("phone") or "—",
        "priority_why": why,
        "boss_brief": brief,
        "situation_kind": kind,
        "hook": hook,
        "sms": rec.get("suggested_sms") or "",
        "reason": reason,
    }


def _all_leads_from_csv(account: dict[str, Any]) -> list[dict[str, Any]]:
    folder = OBS / "GHL" / account["obsidian_folder"] / "Recommendations"
    if not folder.exists():
        return []
    dated = sorted(folder.glob("*-reengage-leads.csv"), reverse=True)
    if not dated:
        return []
    rows: list[dict[str, Any]] = []
    with dated[0].open(encoding="utf-8", newline="") as f:
        for rec in csv.DictReader(f):
            rows.append(_csv_lead_row(rec))
    return rows


def _top_leads_from_csv(account: dict[str, Any], limit: int = DAILY_LIMIT) -> list[dict[str, Any]]:
    return _all_leads_from_csv(account)[:limit]


def _ensure_watch_table(schema: str) -> None:
    sql = f"""
    CREATE TABLE IF NOT EXISTS {schema}.daily_watch (
      contact_id text PRIMARY KEY,
      contact_name text,
      phone text,
      first_seen_on date NOT NULL DEFAULT CURRENT_DATE,
      last_seen_on date NOT NULL DEFAULT CURRENT_DATE,
      last_status text NOT NULL DEFAULT 'open',
      last_priority text,
      last_situation text,
      last_reason text,
      report_count int NOT NULL DEFAULT 0,
      updated_at timestamptz NOT NULL DEFAULT now()
    );
    """
    subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "clawsum-postgres-1",
            "psql",
            "-U",
            "clawsum",
            "-d",
            "ghl",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=sql.encode(),
        check=False,
        capture_output=True,
    )


def _load_open_watch(account: dict[str, Any], password: str) -> list[dict[str, str]]:
    schema = account["schema_prefix"]
    _ensure_watch_table(schema)
    try:
        raw = psql_as_account(
            account,
            password,
            f"SELECT contact_id || E'\\t' || COALESCE(contact_name,'') || E'\\t' || "
            f"COALESCE(phone,'') || E'\\t' || COALESCE(last_priority,'') || E'\\t' || "
            f"COALESCE(last_situation,'') || E'\\t' || COALESCE(last_reason,'') || E'\\t' || "
            f"COALESCE(first_seen_on::text,'') || E'\\t' || report_count::text "
            f"FROM {schema}.daily_watch WHERE last_status = 'open' "
            f"ORDER BY last_seen_on DESC;",
        )
    except RuntimeError:
        return []
    rows: list[dict[str, str]] = []
    for line in (raw or "").splitlines():
        bits = line.split("\t")
        if not bits or not bits[0].strip():
            continue
        rows.append(
            {
                "contact_id": bits[0].strip(),
                "name": bits[1] if len(bits) > 1 else "",
                "phone": bits[2] if len(bits) > 2 else "",
                "last_priority": bits[3] if len(bits) > 3 else "",
                "last_situation": bits[4] if len(bits) > 4 else "",
                "last_reason": bits[5] if len(bits) > 5 else "",
                "first_seen_on": bits[6] if len(bits) > 6 else "",
                "report_count": bits[7] if len(bits) > 7 else "0",
            }
        )
    return rows


def _select_daily_roster(
    leads: list[dict[str, Any]], watch: list[dict[str, str]], limit: int = DAILY_LIMIT
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Updates on prior contacts first, then new contacts, cap at limit."""
    by_id = {L.get("contact_id"): L for L in leads if L.get("contact_id")}
    watch_ids = [w["contact_id"] for w in watch if w.get("contact_id")]
    updates: list[dict[str, Any]] = []
    cleared: list[dict[str, Any]] = []
    for w in watch:
        cid = w.get("contact_id") or ""
        if cid in by_id:
            L = dict(by_id[cid])
            L["lane"] = "update"
            prev_sit = w.get("last_situation") or ""
            now_sit = L.get("situation_kind") or ""
            if prev_sit and now_sit and prev_sit != now_sit:
                L["change_note"] = f"Situation changed {prev_sit} → {now_sit}"
            else:
                L["change_note"] = (
                    f"Still open (day {(int(w.get('report_count') or 0) + 1)} on list)"
                )
            updates.append(L)
        else:
            cleared.append(
                {
                    "contact_id": cid,
                    "name": w.get("name") or cid,
                    "phone": w.get("phone") or "—",
                    "lane": "cleared",
                    "change_note": (
                        "No longer a viable gap — likely worked, moved on, or landline. "
                        f"Last: {w.get('last_priority') or '?'} / {w.get('last_situation') or w.get('last_reason') or '—'}"
                    ),
                }
            )
    new: list[dict[str, Any]] = []
    for L in leads:
        cid = L.get("contact_id")
        if cid and cid not in watch_ids:
            row = dict(L)
            row["lane"] = "new"
            row["change_note"] = "New to the daily list"
            new.append(row)
    selected: list[dict[str, Any]] = []
    for bucket in (updates, new):
        for L in bucket:
            if len(selected) >= limit:
                break
            selected.append(L)
        if len(selected) >= limit:
            break
    return selected, cleared


def _persist_watch(
    account: dict[str, Any],
    password: str,
    selected: list[dict[str, Any]],
    cleared: list[dict[str, Any]],
) -> None:
    schema = account["schema_prefix"]
    _ensure_watch_table(schema)
    today = datetime.now(TZ).date().isoformat()
    for L in selected:
        cid = (L.get("contact_id") or "").replace("'", "''")
        if not cid:
            continue
        name = (L.get("name") or "").replace("'", "''")
        phone = (L.get("phone") or "").replace("'", "''")
        pri = (L.get("priority") or "").replace("'", "''")
        sit = (L.get("situation_kind") or "").replace("'", "''")
        reason = (L.get("reason") or L.get("priority_why") or "").replace("'", "''")[:300]
        sql = f"""
INSERT INTO {schema}.daily_watch (
  contact_id, contact_name, phone, first_seen_on, last_seen_on, last_status,
  last_priority, last_situation, last_reason, report_count, updated_at
) VALUES (
  '{cid}', '{name}', '{phone}', '{today}', '{today}', 'open',
  '{pri}', '{sit}', '{reason}', 1, now()
)
ON CONFLICT (contact_id) DO UPDATE SET
  contact_name = EXCLUDED.contact_name,
  phone = EXCLUDED.phone,
  last_seen_on = EXCLUDED.last_seen_on,
  last_status = 'open',
  last_priority = EXCLUDED.last_priority,
  last_situation = EXCLUDED.last_situation,
  last_reason = EXCLUDED.last_reason,
  report_count = {schema}.daily_watch.report_count + 1,
  updated_at = now();
"""
        try:
            psql_as_account(account, password, sql)
        except RuntimeError as e:
            print(f"WARN watch upsert {cid}: {e}")
    for C in cleared:
        cid = (C.get("contact_id") or "").replace("'", "''")
        if not cid:
            continue
        try:
            psql_as_account(
                account,
                password,
                f"UPDATE {schema}.daily_watch SET last_status = 'cleared', "
                f"last_seen_on = '{today}', updated_at = now() "
                f"WHERE contact_id = '{cid}';",
            )
        except RuntimeError as e:
            print(f"WARN watch clear {cid}: {e}")


def latest_audit_stats(
    account: dict[str, Any], password: str, *, persist_watch: bool = True
) -> dict[str, Any]:
    schema = account["schema_prefix"]
    out: dict[str, Any] = {
        "run_id": None,
        "summary": "",
        "finished_at": "",
        "viable": 0,
        "by_priority": {},
        "conv_gaps": 0,
        "top_leads": [],
        "cleared_leads": [],
        "update_count": 0,
        "new_count": 0,
        "excluded_sample": [],
        "audits_this_week": 0,
    }
    try:
        row = psql_as_account(
            account,
            password,
            f"SELECT id, summary, finished_at::text FROM {schema}.audit_runs "
            f"ORDER BY id DESC LIMIT 1;",
        )
    except RuntimeError as e:
        out["summary"] = f"(postgres unavailable: {e})"
        return out
    if not row or not row.strip():
        return out
    parts = row.strip().split("|")
    if len(parts) < 1:
        return out
    try:
        run_id = int(parts[0].strip())
    except ValueError:
        return out
    out["run_id"] = run_id
    out["summary"] = parts[1].strip() if len(parts) > 1 else ""
    out["finished_at"] = parts[2].strip() if len(parts) > 2 else ""

    try:
        viable = psql_as_account(
            account,
            password,
            f"SELECT COUNT(*) FROM {schema}.reengage_leads WHERE audit_run_id = {run_id};",
        )
        out["viable"] = int((viable or "0").strip() or 0)

        pri = psql_as_account(
            account,
            password,
            f"SELECT priority || ':' || COUNT(*) FROM {schema}.reengage_leads "
            f"WHERE audit_run_id = {run_id} GROUP BY priority;",
        )
        if pri:
            for line in pri.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    out["by_priority"][k.strip()] = int(v.strip() or 0)

        gaps = psql_as_account(
            account,
            password,
            f"SELECT COUNT(*) FROM {schema}.conversation_reviews WHERE audit_run_id = {run_id};",
        )
        out["conv_gaps"] = int((gaps or "0").strip() or 0)

        all_leads = _all_leads_from_csv(account)
        watch = _load_open_watch(account, password)
        if all_leads or watch:
            roster, cleared = _select_daily_roster(all_leads, watch, DAILY_LIMIT)
            out["top_leads"] = roster
            out["cleared_leads"] = cleared
            out["update_count"] = sum(1 for L in roster if L.get("lane") == "update")
            out["new_count"] = sum(1 for L in roster if L.get("lane") == "new")
            if persist_watch:
                _persist_watch(account, password, roster, cleared)
        else:
            tops = psql_as_account(
                account,
                password,
                f"SELECT priority, contact_name, phone, "
                f"COALESCE(priority_why, reason), COALESCE(boss_brief,''), "
                f"COALESCE(situation_kind,''), COALESCE(contact_specific_hook,''), "
                f"COALESCE(suggested_sms,'') "
                f"FROM {schema}.reengage_leads WHERE audit_run_id = {run_id} "
                f"ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
                f"WHEN 'medium' THEN 2 ELSE 3 END, id LIMIT 10;",
            )
            if tops:
                for line in tops.splitlines():
                    bits = [b.strip() for b in line.split("|")]
                    if len(bits) >= 3:
                        out["top_leads"].append(
                            {
                                "priority": bits[0],
                                "name": bits[1],
                                "phone": bits[2],
                                "priority_why": bits[3] if len(bits) > 3 else "",
                                "boss_brief": bits[4] if len(bits) > 4 else "",
                                "situation_kind": bits[5] if len(bits) > 5 else "",
                                "hook": bits[6] if len(bits) > 6 else "",
                                "sms": bits[7] if len(bits) > 7 else "",
                            }
                        )

        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
        week_runs = psql_as_account(
            account,
            password,
            f"SELECT COUNT(*) FROM {schema}.audit_runs "
            f"WHERE finished_at::date >= '{week_ago}'::date;",
        )
        out["audits_this_week"] = int((week_runs or "0").strip() or 0)
    except RuntimeError as e:
        out["summary"] = (out.get("summary") or "") + f" (partial stats: {e})"
    return out


def account_telegram_chat(account: dict[str, Any], env: dict[str, str]) -> str:
    slug_key = account["slug"].upper().replace("-", "_")
    for key in (
        f"GHL_{slug_key}_TELEGRAM_GROUP_ID",
        account.get("env_telegram") or "",
        "TELEGRAM_REPORT_CHAT_ID",
        "TELEGRAM_ADMIN_CHAT_ID",
    ):
        if not key:
            continue
        val = (env.get(key) or "").strip()
        if val:
            return val
    return (account.get("telegram_group_id") or "").strip()


def build_report(
    account: dict[str, Any],
    *,
    location_name: str,
    pipelines: list[dict[str, Any]],
    opps: list[dict[str, Any]],
    stats: dict[str, Any],
    field_note: str,
) -> str:
    now = datetime.now(TZ)
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    stages = stage_counts(pipelines, opps)
    seller_n = sum(n for p, _, n in stages if classify_pipeline(p) == "seller")
    buyer_n = sum(n for p, _, n in stages if classify_pipeline(p) == "buyer")
    other_n = sum(n for p, _, n in stages if classify_pipeline(p) == "other")
    pri = stats.get("by_priority") or {}

    lines = [
        f"# Daily REI report — {account['display_name']}",
        "",
        f"**As of:** {now.strftime('%Y-%m-%d %H:%M %Z')} | **Window start:** {week_start}",
        f"**Location:** {location_name} | **Slug:** `{account['slug']}`",
        f"**Agent:** `{account['id']}`",
        "",
        "## Executive snapshot",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Open opportunities sampled | {len(opps)} |",
        f"| Seller-side open (heuristic) | {seller_n} |",
        f"| Buyer-side open (heuristic) | {buyer_n} |",
        f"| Other / unclassified open | {other_n} |",
        f"| Pipelines | {len(pipelines)} |",
        f"| Viable re-engage (latest audit) | {stats.get('viable', 0)} |",
        f"| Conversation gaps (latest audit) | {stats.get('conv_gaps', 0)} |",
        f"| Audits finished (7d) | {stats.get('audits_this_week', 0)} |",
        f"| Latest audit run | {stats.get('run_id') or '—'} @ {stats.get('finished_at') or '—'} |",
        "",
        "### Priority mix (re-engage)",
        "",
    ]
    if pri:
        for k in ("critical", "high", "medium", "low"):
            if k in pri:
                lines.append(f"- **{k}:** {pri[k]}")
    else:
        lines.append("- (no re-engage rows yet — run audit)")

    lines.extend(["", "## Pipeline by stage (open opps)", ""])
    if not stages:
        lines.append("_No open opportunities returned from MCP (check PIT scope / pipelines)._")
    else:
        lines.append("| Pipeline | Stage | Open | Lane |")
        lines.append("|----------|-------|------|------|")
        for pname, sname, n in stages[:40]:
            lane = classify_pipeline(pname)
            lines.append(f"| {pname[:40]} | {sname[:40]} | {n} | {lane} |")
        if len(stages) > 40:
            lines.append(f"| … | +{len(stages) - 40} more stages | | |")

    lines.extend(
        [
            "",
            "## What to look for this week (REI lens)",
            "",
            "1. **Separate seller vs buyer boards** — mixed pipelines distort conversion.",
            "2. **Speed-to-lead / missed-call text-back** — unanswered inbound &gt;48h is revenue leak.",
            "3. **Landlines** — tag `landline`+`no-sms`; never SMS re-engage.",
            "4. **Hot stages** (Offer / Negotiating / UC) — human follow-up, not cold drip.",
            "5. **Buyer list** — active 90d responders; thin active list slows disposition.",
            "6. **Next action on every open opp** — no stage without a dated task.",
            "",
            f"## Daily roster (top {DAILY_LIMIT} — updates first, then new)",
            "",
            f"Prior contacts still open: **{stats.get('update_count', 0)}** · "
            f"New today: **{stats.get('new_count', 0)}** · "
            f"Cleared since last report: **{len(stats.get('cleared_leads') or [])}**",
            "",
        ]
    )
    tops = stats.get("top_leads") or []
    if not tops:
        lines.append("_No viable re-engage leads in latest audit._")
    else:
        for i, L in enumerate(tops, 1):
            pri = L.get("priority") or "?"
            lane = L.get("lane") or "new"
            badge = "UPDATE" if lane == "update" else "NEW"
            lines.append(f"### {i}. [{badge}] [{pri}] {L.get('name')} ({L.get('phone')})")
            if L.get("change_note"):
                lines.append(f"- **Since last report:** {L.get('change_note')}")
            lines.append(f"- **Why {pri}:** {L.get('priority_why') or '—'}")
            lines.append(f"- **Need to know:** {L.get('boss_brief') or '—'}")
            if L.get("situation_kind"):
                lines.append(f"- **Situation:** {L.get('situation_kind')}")
            lines.append(f"- **Hook (situation, not raw transcript):** {L.get('hook') or '—'}")
            lines.append(f"- **Suggested SMS:** {L.get('sms') or '—'}")
            lines.append("")

    cleared = stats.get("cleared_leads") or []
    if cleared:
        lines.extend(["## Cleared since last report (do not re-work unless they write back)", ""])
        for C in cleared[:15]:
            lines.append(
                f"- **{C.get('name')}** ({C.get('phone')}) — {C.get('change_note')}"
            )
        lines.append("")

    lines.extend(
        [
            "## Recommended seller / buyer posture",
            "",
            "- Sellers: short empathy + address hook + ask for best call time.",
            "- Missed call: text-back immediately; offer call or text.",
            "- Buyers: criteria first; deal alerts only to matching buy box.",
            "- Referrals: serious referrer nurture ≠ seller appointment script.",
            "- Full copy bank: workspace `KNOWLEDGE-REI.md` / Obsidian Playbooks.",
            "",
            "## Automation & field notes",
            "",
            field_note or "_See latest strategic analysis in Audits/._",
            "",
            f"**Latest audit summary:** {stats.get('summary') or '—'}",
            "",
            "## Deliverable paths",
            "",
            f"- Workspace re-engage: `workspace-{account['id']}/REENGAGE.md`",
            f"- Obsidian: `GHL/{account['obsidian_folder']}/Reports/`",
            f"- Knowledge: `GHL/{account['obsidian_folder']}/Playbooks/REI-WHOLESALE-KNOWLEDGE.md`",
            f"- Refresh audit: `python3 /docker/clawsum/scripts/ghl-strategic-audit.py "
            f"--slug {account['slug']} --vertical rei --use-llm`",
            "",
            "## Authority reminder",
            "",
            "- This report is **Tier 0–1** (read / draft).",
            "- SMS sends, tags, pipeline moves → Boss approval (**Tier 2**).",
            "- Do not cross-read another GHL location or schema.",
            "",
        ]
    )
    return "\n".join(lines)


def telegram_digest(account: dict[str, Any], report_md: str, stats: dict[str, Any]) -> str:
    now = datetime.now(TZ)
    pri = stats.get("by_priority") or {}
    lines = [
        f"📊 Daily GHL REI — {account['display_name']}",
        now.strftime("%A %Y-%m-%d %H:%M %Z"),
        "",
        f"Roster: {stats.get('update_count', 0)} updates + {stats.get('new_count', 0)} new "
        f"(cap {DAILY_LIMIT}) · cleared {len(stats.get('cleared_leads') or [])}",
        f"Viable in audit: {stats.get('viable', 0)} "
        f"(crit {pri.get('critical', 0)} / high {pri.get('high', 0)})",
        f"Conversation gaps: {stats.get('conv_gaps', 0)}",
        f"Audit run: {stats.get('run_id') or '—'}",
        "",
        "Today's 10:",
    ]
    for i, L in enumerate((stats.get("top_leads") or [])[:DAILY_LIMIT], 1):
        badge = "UPD" if L.get("lane") == "update" else "NEW"
        lines.append(
            f"{i}. [{badge}] [{L.get('priority')}] {L.get('name')} — "
            f"{(L.get('change_note') or L.get('priority_why') or '')[:80]}"
        )
    lines.extend(
        [
            "",
            "Ask in Telegram for full re-engage → agent reads REENGAGE.md",
            f"Obsidian: GHL/{account['obsidian_folder']}/Reports/",
        ]
    )
    # Keep under Telegram limits; full report is on disk
    body = "\n".join(lines)
    if len(body) > 3500:
        body = body[:3500] + "\n…"
    return body


def write_outputs(account: dict[str, Any], report_md: str, week_stamp: str) -> list[Path]:
    written: list[Path] = []
    folder = OBS / "GHL" / account["obsidian_folder"] / "Reports"
    folder.mkdir(parents=True, exist_ok=True)
    dated = folder / f"{week_stamp}-weekly-report.md"
    latest = folder / "LATEST-WEEKLY-REPORT.md"
    dated.write_text(report_md + "\n", encoding="utf-8")
    latest.write_text(report_md + "\n", encoding="utf-8")
    written.extend([dated, latest])

    ws = ROOT / "data" / ".openclaw" / f"workspace-{account['id']}"
    if ws.exists():
        (ws / "WEEKLY.md").write_text(report_md + "\n", encoding="utf-8")
        notes = ws / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        (notes / "LATEST-WEEKLY-REPORT.md").write_text(report_md + "\n", encoding="utf-8")
        written.append(ws / "WEEKLY.md")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    mirror = REPORT_DIR / f"{account['slug']}-{week_stamp}.md"
    mirror.write_text(report_md + "\n", encoding="utf-8")
    written.append(mirror)
    return written


def seed_knowledge(account: dict[str, Any]) -> Path | None:
    """Ensure KNOWLEDGE-REI.md is in workspace + Obsidian Playbooks."""
    src_candidates = [
        ROOT / "examples" / "instance-overlays" / "REI-WHOLESALE-KNOWLEDGE.md",
        SCRIPT_DIR.parent / "examples" / "instance-overlays" / "REI-WHOLESALE-KNOWLEDGE.md",
    ]
    src = next((p for p in src_candidates if p.exists()), None)
    if not src:
        return None
    text = src.read_text(encoding="utf-8")
    play = OBS / "GHL" / account["obsidian_folder"] / "Playbooks"
    play.mkdir(parents=True, exist_ok=True)
    dest_obs = play / "REI-WHOLESALE-KNOWLEDGE.md"
    dest_obs.write_text(text, encoding="utf-8")
    ws = ROOT / "data" / ".openclaw" / f"workspace-{account['id']}"
    if ws.exists():
        (ws / "KNOWLEDGE-REI.md").write_text(text, encoding="utf-8")
    return dest_obs


def process_account(
    slug: str,
    *,
    do_audit: bool,
    use_llm: bool,
    dry_run: bool,
    notify: bool,
) -> int:
    account = ghl.account_by_slug(slug)
    if not account:
        print(f"FAIL: unknown slug {slug}", file=sys.stderr)
        return 1

    env = load_env()
    pit = env.get(account["env_pit"], "").strip()
    location_id = env.get(account["env_location"], "").strip()
    if not pit or not location_id:
        print(
            f"SKIP {slug}: missing {account['env_pit']} or {account['env_location']} "
            "(agent provisioned; add PIT + locationId to enable CRM reports)",
            file=sys.stderr,
        )
        return 0

    seed_knowledge(account)

    if do_audit:
        rc = run_strategic_audit(slug, use_llm=use_llm)
        if rc != 0:
            print(f"WARN {slug}: strategic audit exited {rc} — continuing with last data")

    password = sync_db_password(account, env)
    available, _ = mcp_tools_list(pit, location_id)
    loc_data = mcp_tool("locations_get-location", {}, pit, location_id, available)
    location_name = account["display_name"]
    if isinstance(loc_data, dict):
        location_name = (
            (loc_data.get("location") or {}).get("name")
            or loc_data.get("name")
            or location_name
        )

    pipelines = fetch_pipelines(pit, location_id, available)
    opps = fetch_opportunities(pit, location_id, available)
    stats = latest_audit_stats(account, password, persist_watch=do_audit)

    # Field note from latest strategic analysis filename if present
    audits = OBS / "GHL" / account["obsidian_folder"] / "Audits"
    field_note = (
        "Read latest `Audits/*-strategic-analysis.md` for field/pipeline/automation recs. "
        "Agent copy bank: `KNOWLEDGE-REI.md`."
    )
    if audits.exists():
        dated = sorted(audits.glob("*-strategic-analysis.md"), reverse=True)
        if dated:
            field_note = f"Latest strategic analysis: `{dated[0].name}` — use with KNOWLEDGE-REI.md checklist."

    report = build_report(
        account,
        location_name=location_name,
        pipelines=pipelines,
        opps=opps,
        stats=stats,
        field_note=field_note,
    )
    week_stamp = datetime.now(TZ).strftime("%Y-%m-%d")
    paths = write_outputs(account, report, week_stamp)
    print(f"OK {slug}: wrote {len(paths)} files")
    for p in paths:
        print(f"  {p}")

    digest = telegram_digest(account, report, stats)
    if dry_run:
        print("--- digest ---")
        print(digest)
        return 0

    if not notify:
        return 0

    chat = account_telegram_chat(account, env)
    try:
        from clawsum_notify import send_telegram, notify_digest, any_ok

        ok = False
        if chat:
            ok = send_telegram(digest, env, chat)
            print(f"Telegram account chat {chat}: {'OK' if ok else 'FAIL'}")
        results = notify_digest(digest, env=env)
        print(f"Notify digest: {results}")
        if not ok and not any_ok(results):
            print(f"WARN {slug}: no notify channel accepted digest", file=sys.stderr)
            return 2
    except Exception as e:  # noqa: BLE001
        print(f"WARN {slug}: notify failed: {e}", file=sys.stderr)
        return 2
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily GHL REI report (MCO + Avenou)")
    parser.add_argument(
        "--slugs",
        default="mco-rei,ave-rei",
        help="Comma-separated slugs, or 'all' for default REI pair",
    )
    parser.add_argument(
        "--audit",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run strategic audit --vertical rei before report (default: on)",
    )
    parser.add_argument("--use-llm", action="store_true", help="Pass --use-llm to audit")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--notify",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Send Telegram/Discord digest (default: on)",
    )
    args = parser.parse_args()

    slugs = parse_slugs(args.slugs)
    if not slugs:
        raise SystemExit("No GHL slugs configured (expected mco-rei / ave-rei)")

    print(f"Daily REI report for: {', '.join(slugs)}")
    worst = 0
    for slug in slugs:
        rc = process_account(
            slug,
            do_audit=args.audit,
            use_llm=args.use_llm,
            dry_run=args.dry_run,
            notify=args.notify and not args.dry_run,
        )
        worst = max(worst, rc)
    raise SystemExit(worst)


if __name__ == "__main__":
    main()
