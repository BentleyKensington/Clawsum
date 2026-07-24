#!/usr/bin/env python3
"""
Triage pending ops.emails → assign domain, create Paperclip tasks, update status.

Uses OPENAI_API_KEY (API) for batch triage cron. OpenClaw Telegram agents still use Codex OAuth.

Usage:
  python3 gmail-triage.py --dry-run --limit 10
  python3 gmail-triage.py --limit 20
  python3 gmail-triage.py --limit 5 --no-create-tasks   # classify only
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"

PAPERCLIP_API = os.environ.get("PAPERCLIP_API", "http://127.0.0.1:3100/api")
COMPANY_ID = os.environ.get(
    "PAPERCLIP_COMPANY_ID", ""
)

def dept_to_agent() -> dict[str, str]:
    mapping = {
        "admin": "Clawsum Admin",
        "coding": "Clawsum Coding",
        "data": "Clawsum Data",
        "realestate": "Clawsum RE",
        "comms": "Clawsum Comms",
        "research": "Clawsum Research",
        "planning": "Clawsum Planning",
    }
    for acc in ghl.accounts():
        mapping[acc["id"]] = acc["paperclip_name"]
    return mapping


def domain_keywords() -> list[tuple[str, list[str]]]:
    rules: list[tuple[str, list[str]]] = []
    for acc in ghl.accounts():
        rules.append((acc["id"], list(acc.get("telegram_needles", []))))
    rules.extend(
        [
            ("realestate", ["real estate", "realestate", "deed", "listing", "comp", "property"]),
            ("ghl", ["ghl", "gohighlevel", "pipeline", "a2p", "crm", "funnel", "vapi"]),
            ("coding", ["script", "deploy", "repo", "code", "api", "mcp", "dns", "cloudflare"]),
            ("data", ["scraper", "analytics", "search console", "bright data", "etl"]),
            ("comms", ["whatsapp", "sms", "campaign", "voice widget"]),
            ("research", ["research", "brief", "competitor"]),
            ("planning", ["roadmap", "priority", "plan"]),
        ]
    )
    return rules


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        out.setdefault(k, v)
    return out


def pg_conn(env: dict):
    import psycopg2

    return psycopg2.connect(
        host=env.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(env.get("POSTGRES_PORT", "5432")),
        dbname=env.get("POSTGRES_DB", "clawsum"),
        user=env.get("POSTGRES_USER", "clawsum"),
        password=env.get("POSTGRES_PASSWORD", ""),
    )


def rule_classify(subject: str, from_addr: str, body: str) -> tuple[str, str, bool]:
    blob = f"{subject} {from_addr} {body}".lower()
    for domain, needles in domain_keywords():
        if any(n in blob for n in needles):
            return domain, f"rule:{domain}", False
    if any(w in blob for w in ("urgent", "asap", "action required", "overdue", "failed")):
        return "admin", "rule:urgent", True
    if any(w in blob for w in ("newsletter", "unsubscribe", "promotion", "no-reply")):
        return "admin", "rule:noise", False
    return "admin", "rule:default", False


def llm_classify(env: dict, subject: str, from_addr: str, snippet: str) -> dict:
    api_key = env.get("OPENAI_API_KEY", "")
    if not api_key:
        return {}
    try:
        import urllib.request

        prompt = {
            "model": env.get("GMAIL_TRIAGE_MODEL", "gpt-4o-mini"),
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Classify admin inbox email for Clawsum multi-agent ops. "
                        "Return JSON: domain (admin|coding|data|realestate|ghl|comms|research|planning), "
                        "action_required (bool), summary (one line), task_title (optional short title for Paperclip)."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"from": from_addr, "subject": subject, "snippet": snippet[:2000]}
                    ),
                },
            ],
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(prompt).encode(),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
        text = data["choices"][0]["message"]["content"]
        return json.loads(text)
    except Exception as e:
        return {"error": str(e)}


def paperclip_api(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{PAPERCLIP_API.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw) if raw else {"error": raw}
        except json.JSONDecodeError:
            return e.code, {"error": raw}


def agent_ids() -> dict[str, str]:
    code, agents = paperclip_api("GET", f"companies/{COMPANY_ID}/agents")
    if code != 200:
        return {}
    return {a["name"]: a["id"] for a in agents if isinstance(a, dict)}


def create_task(
    title: str,
    description: str,
    domain: str,
    by_name: dict[str, str],
    *,
    dry_run: bool,
) -> str | None:
    agent_name = dept_to_agent().get(domain, "Clawsum Admin")
    assignee = by_name.get(agent_name)
    if dry_run:
        print(f"  [dry-run] task -> {agent_name}: {title[:70]}")
        return "dry-run"
    body = {
        "title": title[:200],
        "description": description[:8000],
        "status": "todo",
        "priority": "medium",
    }
    if assignee:
        body["assigneeAgentId"] = assignee
    code, res = paperclip_api("POST", f"companies/{COMPANY_ID}/issues", body)
    if code in (200, 201) and isinstance(res, dict):
        return res.get("id")
    print(f"  task create failed: {code} {res}", file=sys.stderr)
    return None


def domain_to_cell() -> dict[str, str]:
    return {
        "admin": "clawsum-platform",
        "coding": "clawsum-platform",
        "planning": "clawsum-platform",
        "data": "clawsum-platform",
        "research": "clawsum-platform",
        "comms": "acceptai-fastbuy",
        "realestate": "real-estate",
        "ghl": "wnn-client",
    }


def find_person_id(cur, from_addr: str):
    import re

    m = re.search(r"[\w.+-]+@[\w.-]+", from_addr or "")
    if not m:
        return None
    email = m.group(0).lower()
    cur.execute(
        "SELECT id FROM ops.people WHERE lower(primary_email) = %s OR %s = ANY(emails) LIMIT 1",
        (email, email),
    )
    row = cur.fetchone()
    return row[0] if row else None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=15)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-llm", action="store_true", help="Rules only")
    p.add_argument("--no-create-tasks", action="store_true")
    p.add_argument("--action-only", action="store_true", help="Only emails needing action")
    args = p.parse_args()

    env = load_env()
    conn = pg_conn(env)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, gmail_id, from_addr, subject, snippet, body_text, domain_guess
        FROM ops.emails
        WHERE processing_status = 'pending'
        ORDER BY received_at DESC NULLS LAST
        LIMIT %s
        """,
        (args.limit,),
    )
    rows = cur.fetchall()
    by_name = agent_ids()
    processed = 0

    for row in rows:
        eid, gmail_id, from_addr, subject, snippet, body_text, domain_guess = row
        body = (body_text or snippet or "")[:4000]
        domain, reason, action_required = rule_classify(
            subject or "", from_addr or "", body
        )

        triage_notes = reason
        task_title = None

        if not args.no_llm and env.get("OPENAI_API_KEY"):
            llm = llm_classify(env, subject or "", from_addr or "", snippet or body)
            if llm and "error" not in llm:
                domain = llm.get("domain", domain) or domain
                action_required = bool(llm.get("action_required", action_required))
                triage_notes = f"llm:{domain}"
                task_title = llm.get("task_title") or llm.get("summary")
                if llm.get("summary"):
                    triage_notes += f" — {llm['summary'][:200]}"

        if args.action_only and not action_required:
            status = "triaged"
            issue_id = None
        elif action_required and not args.no_create_tasks:
            title = task_title or f"Email: {(subject or '(no subject)')[:80]}"
            desc = (
                f"Gmail triage (auto)\n\n"
                f"From: {from_addr}\n"
                f"Subject: {subject}\n\n"
                f"{snippet or body[:1500]}\n\n"
                f"gmail_id: {gmail_id}"
            )
            issue_id = create_task(title, desc, domain, by_name, dry_run=args.dry_run)
            status = "linked_task" if issue_id else "action_required"
        else:
            status = "triaged"
            issue_id = None

        agent_name = dept_to_agent().get(domain, "Clawsum Admin")
        cell_slug = domain_to_cell().get(domain, "clawsum-platform")
        print(f"{gmail_id[:12]}… {status} -> {domain}/{cell_slug} ({agent_name}) {subject[:50] if subject else ''}")

        person_id = None
        business_id = None
        if not args.dry_run:
            try:
                cur.execute("SELECT id FROM ops.businesses WHERE slug = %s", (cell_slug,))
                brow = cur.fetchone()
                business_id = brow[0] if brow else None
                person_id = find_person_id(cur, from_addr or "")
            except Exception:
                pass

            cur.execute(
                """
                UPDATE ops.emails SET
                  processing_status = %s,
                  domain_guess = %s,
                  assigned_agent = %s,
                  triage_notes = %s,
                  paperclip_issue_id = COALESCE(%s, paperclip_issue_id),
                  business_id = COALESCE(%s, business_id),
                  person_id = COALESCE(%s, person_id)
                WHERE id = %s
                """,
                (
                    status,
                    domain,
                    domain,
                    triage_notes,
                    issue_id if issue_id and issue_id != "dry-run" else None,
                    business_id,
                    person_id,
                    eid,
                ),
            )
        processed += 1

    if not args.dry_run:
        conn.commit()
    cur.execute("SELECT COUNT(*) FROM ops.emails WHERE processing_status = 'pending'")
    pending = cur.fetchone()[0]
    conn.close()
    print(f"Processed {processed}. Pending remaining: {pending}")


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print("pip3 install psycopg2-binary", file=sys.stderr)
        raise SystemExit(1) from e
