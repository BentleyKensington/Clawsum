#!/usr/bin/env python3
"""
Deep inbox analysis — LLM + enterprise context (+ optional web research).

Upgrades ops.emails / ops.email_reviews with:
  - full narrative (analysis_report)
  - value_assessment, suggested_actions, research_notes in analysis_json
  - enterprise reconciliation against cells/people/authority

Usage (VPS):
  python3 /docker/clawsum/scripts/gmail-inbox-deep-review.py --needs-boss --limit 40
  python3 /docker/clawsum/scripts/gmail-inbox-deep-review.py --all-inbox --limit 100
  python3 /docker/clawsum/scripts/gmail-inbox-deep-review.py --gmail-id <id>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Need psycopg2", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
AUTHORITY = (
    ROOT / "paperclip-data/.hermes/plugins/clawsum-cockpit/dashboard/authority.json"
)
AUTHORITY_ALT = (
    ROOT / "examples/hermes-cockpit/plugin/clawsum-cockpit/dashboard/authority.json"
)


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        out.setdefault(k, v)
    return out


def pg(env: dict):
    return psycopg2.connect(
        host=env.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(env.get("POSTGRES_PORT", "5432") or "5432"),
        user=env.get("POSTGRES_USER", "clawsum"),
        password=env.get("POSTGRES_PASSWORD", ""),
        dbname=env.get("POSTGRES_DB", "clawsum"),
    )


def load_authority() -> dict:
    for p in (AUTHORITY, AUTHORITY_ALT):
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
    return {}


def enterprise_brief(cur, auth: dict) -> str:
    cur.execute(
        "SELECT slug, name, type FROM ops.businesses WHERE active ORDER BY slug LIMIT 40"
    )
    cells = [dict(r) for r in cur.fetchall()]
    cur.execute(
        """
        SELECT display_name, kind, primary_email, company_name
        FROM ops.people WHERE active
        ORDER BY kind, display_name LIMIT 80
        """
    )
    people = [dict(r) for r in cur.fetchall()]
    agents = (auth.get("agents") or [])[:20]
    skills = (auth.get("skills") or [])[:40]
    return json.dumps(
        {
            "cells": cells,
            "people": people,
            "agents": [
                {"id": a.get("id"), "name": a.get("name"), "domains": a.get("domains")}
                for a in agents
                if isinstance(a, dict)
            ],
            "skills_sample": [
                {"id": s.get("id"), "agents": s.get("agents")}
                for s in skills
                if isinstance(s, dict)
            ],
            "stack": "Hermes talks · Paperclip manages · OpenClaw acts · Authelia SSO",
        },
        indent=2,
    )[:12000]


def duckduckgo_brief(query: str) -> str:
    """Lightweight public search via DuckDuckGo Instant Answer (no key)."""
    q = (query or "").strip()
    if not q:
        return ""
    try:
        url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(
            {"q": q[:180], "format": "json", "no_html": 1, "skip_disambig": 1}
        )
        req = urllib.request.Request(url, headers={"User-Agent": "ClawsumDeepReview/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode())
        bits = []
        if data.get("AbstractText"):
            bits.append(data["AbstractText"][:600])
        for t in (data.get("RelatedTopics") or [])[:4]:
            if isinstance(t, dict) and t.get("Text"):
                bits.append(t["Text"][:240]
                )
            elif isinstance(t, dict) and isinstance(t.get("Topics"), list):
                for st in t["Topics"][:2]:
                    if isinstance(st, dict) and st.get("Text"):
                        bits.append(st["Text"][:240])
        return "\n".join(bits)[:1500]
    except Exception as e:
        return f"(research unavailable: {e})"


def llm_deep(env: dict, payload: dict) -> dict:
    api_key = env.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "OPENAI_API_KEY missing"}
    model = env.get("GMAIL_DEEP_MODEL") or env.get("GMAIL_TRIAGE_MODEL") or "gpt-4o-mini"
    system = (
        "You are Clawsum's CEO inbox analyst for Gerald (Boss). "
        "Clawsum is a personal CEO overwatch system: Hermes talks, Paperclip manages tasks, "
        "OpenClaw acts, Authelia SSO guards ops. Businesses are isolated cells. "
        "Read the email body carefully. Reconcile against the enterprise brief (cells, people, agents). "
        "Research notes may be provided — use them when relevant; say when you need more research. "
        "Return STRICT JSON with keys:\n"
        "  intent (string),\n"
        "  summary (2-5 sentences),\n"
        "  value_assessment (does this offer value to Clawsum/Gerald? why/why not),\n"
        "  suggested_actions (array of concrete next steps),\n"
        "  research_notes (what you inferred / what to look up),\n"
        "  priority (urgent|high|medium|low),\n"
        "  review_status (needs_boss|reviewed|ignored),\n"
        "  action_required (bool),\n"
        "  business_slug (best cell slug or null),\n"
        "  questions_for_boss (array of short questions),\n"
        "  narrative (markdown report, extensive: context, enterprise fit, risks, recommendation).\n"
        "Do not invent Paperclip issue IDs. Be specific and CEO-useful."
    )
    body = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload)[:90000]},
        ],
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode())
        text = data["choices"][0]["message"]["content"]
        return json.loads(text)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:400]}"}
    except Exception as e:
        return {"error": str(e)}


def render_report(email: dict, analysis: dict, research: str) -> str:
    narrative = analysis.get("narrative") or ""
    if narrative.strip():
        base = narrative.strip()
    else:
        base = (
            f"## {email.get('subject') or '(no subject)'}\n\n"
            f"**Intent:** {analysis.get('intent')}\n\n"
            f"**Summary:** {analysis.get('summary')}\n\n"
            f"**Value:** {analysis.get('value_assessment')}\n\n"
            f"**Recommendation priority:** {analysis.get('priority')}\n"
        )
    actions = analysis.get("suggested_actions") or []
    qs = analysis.get("questions_for_boss") or []
    extra = [
        "",
        "---",
        f"- **Gmail id:** `{email.get('gmail_id')}`",
        f"- **From:** {email.get('from_addr')}",
        f"- **Received:** {email.get('received_at')}",
        f"- **Cell guess:** `{analysis.get('business_slug') or email.get('business_slug') or '—'}`",
        f"- **Deep review:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "### Suggested actions",
    ]
    if actions:
        for a in actions:
            extra.append(f"- {a}")
    else:
        extra.append("- (none)")
    extra += ["", "### Questions for Boss"]
    if qs:
        for q in qs:
            extra.append(f"- {q}")
    else:
        extra.append("- (none)")
    if research:
        extra += ["", "### Research brief used", research[:1200]]
    # Original body appendix
    body = (email.get("body_text") or email.get("snippet") or "").strip()
    if body:
        extra += ["", "### Original message (text)", "```", body[:20000], "```"]
    return base + "\n" + "\n".join(extra)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--needs-boss", action="store_true")
    ap.add_argument("--all-inbox", action="store_true")
    ap.add_argument("--gmail-id")
    ap.add_argument("--research", action="store_true", default=True)
    ap.add_argument("--no-research", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    do_research = args.research and not args.no_research

    env = load_env()
    if not env.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY required", file=sys.stderr)
        raise SystemExit(2)

    auth = load_authority()
    conn = pg(env)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    brief = enterprise_brief(cur, auth)

    where = ["(mailbox IS NULL OR mailbox = %s)"]
    params: list = [env.get("GMAIL_ADMIN_ADDRESS", "clawsums@gmail.com")]
    if args.gmail_id:
        where = ["gmail_id = %s"]
        params = [args.gmail_id]
    elif args.needs_boss:
        where.append("review_status = 'needs_boss'")
    elif args.all_inbox:
        where.append("COALESCE(is_inbox, true)")
    else:
        where.append(
            "(review_status = 'needs_boss' OR processing_status IN ('pending','action_required') "
            "OR analysis_report IS NULL OR analysis_report = '')"
        )

    cur.execute(
        f"""
        SELECT e.id, e.gmail_id, e.subject, e.from_addr, e.snippet, e.body_text,
               e.received_at, e.review_status, e.processing_status, e.analysis_report,
               b.slug AS business_slug, p.display_name AS person_name
        FROM ops.emails e
        LEFT JOIN ops.businesses b ON b.id = e.business_id
        LEFT JOIN ops.people p ON p.id = e.person_id
        WHERE {' AND '.join(where)}
        ORDER BY e.received_at DESC NULLS LAST
        LIMIT %s
        """,
        tuple(params + [args.limit]),
    )
    rows = [dict(r) for r in cur.fetchall()]
    print(f"deep-review candidates={len(rows)} model={env.get('GMAIL_DEEP_MODEL') or 'gpt-4o-mini'}")

    ok = 0
    for em in rows:
        subj = em.get("subject") or ""
        from_addr = em.get("from_addr") or ""
        research = ""
        if do_research:
            # Prefer org / product cues from subject+from domain
            dom = ""
            m = re.search(r"@([\w.-]+)", from_addr)
            if m:
                dom = m.group(1)
            q = f"{subj} {dom}".strip()
            research = duckduckgo_brief(q)

        print(f"- {em.get('gmail_id')}: {(subj or '')[:70]}")
        try:
            import clawsum_analyst

            cur.execute("SELECT attachments FROM ops.emails WHERE id = %s", (em["id"],))
            att_row = cur.fetchone() or {}
            parsed = clawsum_analyst.analyze_email(
                env,
                {
                    "subject": subj,
                    "from_addr": from_addr,
                    "body_text": em.get("body_text") or em.get("snippet") or "",
                    "snippet": em.get("snippet") or "",
                    "received_at": em.get("received_at"),
                    "attachments": att_row.get("attachments") if isinstance(att_row, dict) else [],
                },
                cur=cur,
            )
            if parsed.get("error"):
                print(f"  FAIL {parsed['error']}", file=sys.stderr)
                continue
            analysis = {
                "intent": parsed.get("intent") or parsed.get("take"),
                "summary": parsed.get("summary"),
                "value_assessment": parsed.get("take"),
                "suggested_actions": parsed.get("suggestions") or [],
                "research_notes": parsed.get("repo_notes") or research,
                "priority": parsed.get("priority"),
                "review_status": parsed.get("review_status"),
                "action_required": parsed.get("action_required"),
                "business_slug": em.get("business_slug"),
                "questions_for_boss": parsed.get("questions") or [],
                "narrative": parsed.get("report_markdown"),
            }
        except Exception as exc:
            print(f"  FAIL analyst {exc}", file=sys.stderr)
            continue
        if analysis.get("error"):
            print(f"  FAIL {analysis['error']}", file=sys.stderr)
            continue

        report = analysis.get("narrative") or render_report(em, analysis, research)
        priority = analysis.get("priority") or "medium"
        if priority not in ("urgent", "high", "medium", "low"):
            priority = "medium"
        review_status = analysis.get("review_status") or "needs_boss"
        if review_status not in ("needs_boss", "reviewed", "ignored", "unreviewed"):
            review_status = "needs_boss"
        intent = (analysis.get("intent") or "")[:2000]
        summary = (analysis.get("summary") or "")[:4000]
        recommendation = "; ".join(
            str(a) for a in (analysis.get("suggested_actions") or [])[:6]
        )[:4000]
        questions = analysis.get("questions_for_boss") or []
        if not isinstance(questions, list):
            questions = [str(questions)]
        analysis_json = {
            "style": "chatgpt",
            "take": analysis.get("value_assessment"),
            "value_assessment": analysis.get("value_assessment"),
            "suggested_actions": analysis.get("suggested_actions") or [],
            "research_notes": analysis.get("research_notes") or research,
            "deep_model": env.get("GMAIL_DEEP_MODEL") or "gpt-4o-mini",
            "deep_reviewed_at": datetime.now(timezone.utc).isoformat(),
            "raw": {k: analysis.get(k) for k in ("intent", "priority", "business_slug", "action_required")},
        }

        if args.dry_run:
            print(f"  [dry-run] priority={priority} status={review_status} report_chars={len(report)}")
            ok += 1
            continue

        cur.execute(
            """
            UPDATE ops.emails SET
              analysis_summary = %s,
              analysis_intent = %s,
              analysis_recommendation = %s,
              analysis_priority = %s,
              analysis_report = %s,
              analysis_json = %s::jsonb,
              review_status = %s,
              reviewed_at = now(),
              processing_status = CASE
                WHEN %s THEN 'action_required'
                WHEN %s = 'ignored' THEN 'ignored'
                ELSE COALESCE(processing_status, 'triaged')
              END
            WHERE id = %s
            """,
            (
                summary,
                intent,
                recommendation or analysis.get("value_assessment") or "",
                priority,
                report,
                json.dumps(analysis_json),
                review_status,
                bool(analysis.get("action_required")),
                review_status,
                em["id"],
            ),
        )
        cur.execute(
            """
            INSERT INTO ops.email_reviews (
              email_id, gmail_id, mailbox, business_slug, review_status, priority,
              is_noise, action_required, intent, summary, recommendation, questions,
              signals, report_markdown, analysis_json, analyzed_at
            ) VALUES (
              %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s,
              %s, %s, %s::jsonb, now()
            )
            ON CONFLICT (email_id) DO UPDATE SET
              review_status = EXCLUDED.review_status,
              priority = EXCLUDED.priority,
              action_required = EXCLUDED.action_required,
              intent = EXCLUDED.intent,
              summary = EXCLUDED.summary,
              recommendation = EXCLUDED.recommendation,
              questions = EXCLUDED.questions,
              signals = EXCLUDED.signals,
              report_markdown = EXCLUDED.report_markdown,
              analysis_json = EXCLUDED.analysis_json,
              analyzed_at = now()
            """,
            (
                em["id"],
                em.get("gmail_id"),
                env.get("GMAIL_ADMIN_ADDRESS", "clawsums@gmail.com"),
                analysis.get("business_slug") or em.get("business_slug"),
                review_status,
                priority,
                review_status == "ignored",
                bool(analysis.get("action_required")),
                intent,
                summary,
                recommendation,
                questions[:12],
                ["deep_llm", "enterprise_reconcile"] + (["research"] if research else []),
                report,
                json.dumps(analysis_json),
            ),
        )
        conn.commit()
        ok += 1
        print(f"  ok priority={priority} status={review_status}")

    cur.close()
    conn.close()
    print(f"done ok={ok}/{len(rows)}")


if __name__ == "__main__":
    main()
