#!/usr/bin/env python3
"""
Analyze Paperclip issues (master list + Gmail tasks): auto-assign agents,
enrich descriptions, post Boss clarification questions, unblock → todo.

Usage:
  python3 paperclip-analyze-assign-boss.py --dry-run --limit 5
  python3 paperclip-analyze-assign-boss.py
  python3 paperclip-analyze-assign-boss.py --gmail-pending 20
  python3 paperclip-analyze-assign-boss.py --status blocked,todo --force
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl  # noqa: E402

API = os.environ.get("PAPERCLIP_API", "http://127.0.0.1:3100/api")
COMPANY_ID = os.environ.get(
    "PAPERCLIP_COMPANY_ID", ""
)

AGENT_NAMES = ghl.paperclip_agent_names()

NAME_TO_KEY = ghl.paperclip_name_to_openclaw_id()

ANALYZED_MARKER = "<!-- clawsum-analyzed:"


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


def api(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw) if raw else {"error": raw}
        except json.JSONDecodeError:
            return e.code, {"error": raw}


def agent_map() -> dict[str, str]:
    code, agents = api("GET", f"companies/{COMPANY_ID}/agents")
    if code != 200 or not isinstance(agents, list):
        return {}
    return {a["name"]: a["id"] for a in agents if isinstance(a, dict)}


def list_issues(statuses: list[str]) -> list[dict]:
    out: list[dict] = []
    for st in statuses:
        code, issues = api("GET", f"companies/{COMPANY_ID}/issues?status={st}&limit=500")
        if code == 200 and isinstance(issues, list):
            out.extend(issues)
    # Dedupe by id
    seen: set[str] = set()
    deduped = []
    for i in out:
        if i["id"] not in seen:
            seen.add(i["id"])
            deduped.append(i)
    return deduped


def already_analyzed(description: str) -> bool:
    return ANALYZED_MARKER in (description or "")


def llm_analyze(env: dict, issue: dict) -> dict:
    api_key = env.get("OPENAI_API_KEY", "")
    if not api_key:
        return fallback_analyze(issue)

    title = issue.get("title") or ""
    desc = (issue.get("description") or "")[:6000]
    ident = issue.get("identifier") or issue.get("id", "")[:8]

    system = (
        "You triage work for Clawsum, a multi-agent ops platform. "
        "Return ONLY valid JSON with keys:\n"
        "  assignee_agent: one of "
        + json.dumps(AGENT_NAMES)
        + "\n"
        "  priority: low|medium|high|urgent\n"
        "  objective: clear 1-2 sentence goal for the assignee\n"
        "  definition_of_done: array of 2-5 concrete completion criteria\n"
        "  boss_questions: array of 3-5 specific questions for the human Boss "
        "(what exactly to deliver, constraints, deadline, budget, who else is involved)\n"
        "  suggested_timeline: string (e.g. 'this week', 'by June 15', 'backlog/no rush')\n"
        "  category: master_list|gmail|ops|research|other\n"
        "  llm_tier: default|cheap|frontier|coding|research|glm\n"
        "    default=interactive Codex path; cheap/free=batch OpenRouter free tier;\n"
        "    frontier=paid Claude/Gemini; coding=Qwen3 Coder; glm=multilingual GLM\n"
        "Pick the specialist agent that should EXECUTE the work (not Paperclip unless orchestration)."
    )
    user = json.dumps(
        {
            "identifier": ident,
            "title": title,
            "description": desc,
            "current_status": issue.get("status"),
            "is_gmail": "gmail_id:" in desc.lower() or "gmail triage" in desc.lower(),
            "delegated_from": "Delegated from" in desc,
        }
    )

    payload = {
        "model": env.get("TASK_ANALYZE_MODEL", "gpt-4o-mini"),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
        text = data["choices"][0]["message"]["content"]
        parsed = json.loads(text)
        if parsed.get("assignee_agent") not in AGENT_NAMES:
            parsed["assignee_agent"] = "Clawsum Admin"
        return parsed
    except Exception as e:
        return {**fallback_analyze(issue), "llm_error": str(e)}


def fallback_analyze(issue: dict) -> dict:
    title = issue.get("title") or ""
    desc = issue.get("description") or ""
    blob = f"{title} {desc}"
    agent = _rule_agent(blob)
    return {
        "assignee_agent": agent,
        "priority": "medium",
        "objective": title[:300],
        "definition_of_done": ["Boss confirms scope", "Deliverable documented in Obsidian or Paperclip"],
        "boss_questions": [
            "What is the exact deliverable you want?",
            "What is the deadline or priority relative to other work?",
            "Who should be notified when this is done?",
            "Any budget, vendor, or legal constraints?",
        ],
        "suggested_timeline": "pending Boss confirmation",
        "category": "gmail" if "gmail_id:" in desc.lower() else "other",
        "llm_tier": "cheap" if "gmail" in title.lower() else "default",
    }


def _rule_agent(blob: str) -> str:
    low = blob.lower()
    ghl_agent = ghl.guess_ghl_paperclip_agent(blob)
    if ghl_agent:
        return ghl_agent
    if any(n in low for n in ghl.GHL_GENERIC_KEYWORDS):
        return "Clawsum Admin"
    rules = [
        ("Clawsum RE", ["deed", "osage", "real estate", "property", "listing", "wanted poster"]),
        ("Clawsum Coding", ["mcp", "claude", "code", "deploy", "cloudflare", "dns", "script", "api"]),
        ("Clawsum Data", ["scraper", "analytics", "search console", "etl", "bright data"]),
        ("Clawsum Comms", ["whatsapp", "voice", "sms", "cell phone"]),
        ("Clawsum Research", ["research", "recording", "brief", "geo audit"]),
        ("Clawsum Planning", ["roadmap", "priority", "plan"]),
    ]
    for name, needles in rules:
        if any(n in low for n in needles):
            return name
    return "Clawsum Admin"


def build_description(issue: dict, analysis: dict) -> str:
    old = issue.get("description") or ""
    # Strip prior analysis block
    if ANALYZED_MARKER in old:
        old = old.split(ANALYZED_MARKER)[0].rstrip()

    done = analysis.get("definition_of_done") or []
    done_md = "\n".join(f"- {x}" for x in done) if isinstance(done, list) else str(done)
    llm_tier = analysis.get("llm_tier") or "default"
    if llm_tier not in ("default", "cheap", "free", "frontier", "coding", "research", "glm"):
        llm_tier = "default"

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    block = f"""
{ANALYZED_MARKER} {ts} -->

## Objective (auto-analyzed)
{analysis.get("objective", "")}

## Definition of done
{done_md}

## Suggested timeline
{analysis.get("suggested_timeline", "TBD")}

## Category
{analysis.get("category", "other")}

## LLM tier
llm:{llm_tier}

---
*Reply to the Boss clarification comment, then ops moves this to todo/in_progress and enables heartbeats.*
""".strip()
    return f"{old}\n\n{block}".strip()


def build_boss_comment(ident: str, title: str, analysis: dict) -> str:
    questions = analysis.get("boss_questions") or []
    if isinstance(questions, str):
        questions = [questions]
    q_md = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))

    return f"""## Boss — clarification needed ({ident})

**Task:** {title[:200]}

**Proposed owner:** {analysis.get("assignee_agent", "Clawsum Admin")}
**Proposed priority:** {analysis.get("priority", "medium")}
**Suggested timeline:** {analysis.get("suggested_timeline", "TBD")}

### What we think this is
{analysis.get("objective", "")}

### Please answer (reply on this issue)
{q_md}

---
*After you reply, assignee will pick up in Boss UI or via heartbeat. Say "approved as written" to skip further questions.*
"""


def process_issue(
    issue: dict,
    by_name: dict[str, str],
    env: dict,
    *,
    dry_run: bool,
    force: bool,
) -> tuple[bool, str]:
    iid = issue["id"]
    ident = issue.get("identifier") or iid[:8]
    title = issue.get("title") or "(untitled)"

    if not force and already_analyzed(issue.get("description") or ""):
        print(f"  skip {ident} (already analyzed)")
        return False, ""

    print(f"  analyze {ident}: {title[:60]}…")
    analysis = llm_analyze(env, issue)
    agent_name = analysis.get("assignee_agent", "Clawsum Admin")
    assignee_id = by_name.get(agent_name) or by_name.get("Clawsum Admin")

    new_desc = build_description(issue, analysis)
    boss_comment = build_boss_comment(ident, title, analysis)
    priority = analysis.get("priority", "medium")
    if priority not in ("low", "medium", "high", "urgent"):
        priority = "medium"

    if dry_run:
        print(f"    -> {agent_name} | {priority} | {len(analysis.get('boss_questions', []))} questions")
        return True, agent_name

    patch_body: dict = {
        "status": "backlog",
        "priority": priority,
        "description": new_desc[:24000],
        "comment": boss_comment[:16000],
    }
    if assignee_id:
        patch_body["assigneeAgentId"] = assignee_id

    code, res = api("PATCH", f"issues/{iid}", patch_body)
    if code != 200:
        # Fallback: PATCH without combined comment, then POST comment
        patch_body.pop("comment", None)
        code, res = api("PATCH", f"issues/{iid}", patch_body)
        if code != 200:
            print(f"    PATCH failed {code}: {res}", file=sys.stderr)
            return False, agent_name
        code2, _ = api("POST", f"issues/{iid}/comments", {"body": boss_comment[:16000]})
        if code2 not in (200, 201):
            print(f"    comment POST {code2}", file=sys.stderr)

    print(f"    OK -> {agent_name} todo + Boss questions")
    return True, agent_name


def triage_pending_gmail(env: dict, by_name: dict[str, str], limit: int, dry_run: bool) -> int:
    """Run gmail triage for pending emails (creates tasks with assignees)."""
    script = ROOT / "scripts/gmail-triage.py"
    if not script.exists():
        return 0
    import subprocess
    import sys as _sys

    cmd = [_sys.executable, str(script), "--limit", str(limit)]
    if dry_run:
        cmd.append("--dry-run")
    print(f"Gmail triage: {' '.join(cmd)}")
    subprocess.run(cmd, check=False)
    return limit


def create_boss_summary_issue(
    processed: list[tuple[str, str, str]],
    by_name: dict[str, str],
    dry_run: bool,
) -> None:
    if not processed:
        return
    lines = [
        "# Boss inbox — clarification batch",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat()}",
        "",
        "The following tasks need your answers **on each issue's comment thread**:",
        "",
    ]
    for ident, title, agent in processed:
        lines.append(f"- **{ident}** — {title[:80]} → *{agent}*")
    lines.append("")
    lines.append("Open Boss UI (`localhost:3100` tunnel) and reply on each task.")

    body = "\n".join(lines)
    title = f"Boss clarifications — {len(processed)} tasks ({datetime.now(timezone.utc):%Y-%m-%d})"

    if dry_run:
        print(f"[dry-run] summary issue: {title}")
        return

    admin_id = by_name.get("Clawsum Admin")
    payload = {
        "title": title[:200],
        "description": body[:24000],
        "status": "todo",
        "priority": "high",
    }
    if admin_id:
        payload["assigneeUserId"] = None  # Boss human — leave unassigned agent
    code, res = api("POST", f"companies/{COMPANY_ID}/issues", payload)
    if code in (200, 201) and isinstance(res, dict):
        iid = res["id"]
        api(
            "POST",
            f"issues/{iid}/comments",
            {
                "body": (
                    "## Boss\n\n"
                    "This is your **master clarification checklist**. "
                    "Work through linked tasks below; each has specific questions in its comments.\n\n"
                    + body[:12000]
                )
            },
        )
        print(f"Created summary issue {res.get('identifier', iid[:8])}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=0, help="Max issues to process (0=all)")
    p.add_argument("--force", action="store_true", help="Re-analyze even if marked")
    p.add_argument("--status", default="blocked,todo,backlog")
    p.add_argument("--gmail-pending", type=int, default=0, metavar="N")
    p.add_argument("--no-summary", action="store_true")
    p.add_argument("--sleep", type=float, default=0.5, help="Seconds between LLM calls")
    args = p.parse_args()

    env = load_env()
    by_name = agent_map()
    if not by_name:
        print("Could not load agents", file=sys.stderr)
        raise SystemExit(1)

    if args.gmail_pending > 0:
        triage_pending_gmail(env, by_name, args.gmail_pending, args.dry_run)

    statuses = [s.strip() for s in args.status.split(",") if s.strip()]
    issues = list_issues(statuses)
    # Prefer master-list children and gmail; skip summary issues we create
    issues.sort(
        key=lambda i: (
            0 if "Delegated from" in (i.get("description") or "") else 1,
            0 if "gmail" in (i.get("description") or "").lower() else 1,
            i.get("issueNumber") or 0,
        )
    )

    if args.limit > 0:
        issues = issues[: args.limit]

    print(f"Processing {len(issues)} issues (statuses: {statuses})")
    processed: list[tuple[str, str, str]] = []
    n = 0
    for issue in issues:
        if "Boss clarifications —" in (issue.get("title") or ""):
            continue
        ok, agent_name = process_issue(
            issue, by_name, env, dry_run=args.dry_run, force=args.force
        )
        if ok:
            ident = issue.get("identifier") or "?"
            processed.append((ident, issue.get("title") or "", agent_name))
            n += 1
        if not args.dry_run and args.sleep > 0:
            time.sleep(args.sleep)

    if not args.no_summary:
        create_boss_summary_issue(processed, by_name, args.dry_run)

    print(f"Done. Analyzed/updated {n} issues.")


if __name__ == "__main__":
    import sys

    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
