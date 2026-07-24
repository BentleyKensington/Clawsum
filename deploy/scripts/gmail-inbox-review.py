#!/usr/bin/env python3
"""
Full-inbox review for clawsums@gmail.com — every email gets a review + analysis report.

For each message:
  - classify cell / person / noise / action
  - write analysis_summary, intent, recommendation, priority
  - persist markdown report on ops.emails + ops.email_reviews
  - optionally create ops.tasks + reminders for action items

Does NOT dump bodies into Hermes memory.

Usage:
  python3 gmail-inbox-review.py --inbox-only --markdown
  python3 gmail-inbox-review.py --all --per-email-report
  python3 gmail-inbox-review.py --sync-first --create-reminders
  python3 gmail-inbox-review.py --report-dir /tmp/inbox-reports
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from email.utils import parseaddr
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Need psycopg2", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
SCRIPTS = Path(__file__).resolve().parent

DOMAIN_TO_CELL = {
    "admin": "clawsum-platform",
    "coding": "clawsum-platform",
    "planning": "clawsum-platform",
    "data": "clawsum-platform",
    "research": "clawsum-platform",
    "comms": "acceptai-fastbuy",
    "realestate": "real-estate",
    "ghl": "wnn-client",
    "wnn": "wnn-client",
    "vocalitic": "vocalitic",
    "roofing": "roofing-os",
    "techtasia": "techtasia",
    "fastbuy": "acceptai-fastbuy",
    "acceptai": "acceptai-fastbuy",
}

CELL_NEEDLES = [
    ("wnn-client", ["wnn", "gohighlevel", "ghl", "closebot", "hyros"]),
    ("vocalitic", ["vocalitic", "signalwire", "latency"]),
    ("roofing-os", ["roofing", "ceoroof", "hail", "storm"]),
    ("techtasia", ["techtasia"]),
    ("acceptai-fastbuy", ["acceptai", "fastbuy", "shopify"]),
    ("real-estate", ["listing", "comp ", "acquisition", "deed"]),
    ("hardware-local-ai", ["gpu", "vram", "ollama", "vllm"]),
    ("personal-admin", ["personal", "family", "doctor", "vacation"]),
    ("clawsum-platform", ["clawsum", "paperclip", "hermes", "openclaw", "traefik"]),
]

NOISE = (
    "newsletter",
    "unsubscribe",
    "no-reply",
    "noreply",
    "donotreply",
    "do-not-reply",
    "promotion",
    "marketing",
    "digest",
    "% off",
    "view in browser",
)
ACTION = (
    "urgent",
    "asap",
    "action required",
    "please review",
    "please confirm",
    "overdue",
    "invoice",
    "payment due",
    "sign here",
    "approval needed",
    "respond by",
    "deadline",
)
QUESTION_CUES = ("?", "can you", "could you", "let me know", "thoughts", "confirm")
MONEY_CUES = ("invoice", "$", "payment", "wire", "refund", "quote", "pricing")
SECURITY_CUES = ("password", "credential", "2fa", "verify your account", "suspicious")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    out.update(os.environ)
    return out


def connect():
    env = load_env()
    return psycopg2.connect(
        host=env.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(env.get("POSTGRES_PORT", "5432")),
        user=env.get("POSTGRES_USER", "clawsum"),
        password=env.get("POSTGRES_PASSWORD", ""),
        dbname=env.get("POSTGRES_DB", "clawsum"),
    )


def extract_email(from_addr: str) -> str:
    _, addr = parseaddr(from_addr or "")
    return (addr or "").strip().lower()


def guess_cell(subject: str, from_addr: str, body: str, domain_guess: str | None) -> str:
    blob = f"{subject} {from_addr} {body}".lower()
    if domain_guess and domain_guess in DOMAIN_TO_CELL:
        return DOMAIN_TO_CELL[domain_guess]
    for slug, needles in CELL_NEEDLES:
        if any(n in blob for n in needles):
            return slug
    return "clawsum-platform"


def analyze_email(
    *,
    subject: str,
    from_raw: str,
    body: str,
    snippet: str,
    processing_status: str,
    domain_guess: str | None,
    paperclip_issue_id: str | None,
    is_inbox: bool,
    gmail_id: str,
    received_at,
    mailbox: str,
) -> dict:
    blob = f"{subject} {from_raw} {body}".lower()
    email = extract_email(from_raw)
    cell = guess_cell(subject, from_raw, body, domain_guess)
    signals: list[str] = []

    is_noise = any(n in blob for n in NOISE) and not any(n in blob for n in ACTION)
    if is_noise:
        signals.append("noise_pattern")
    action = False
    if processing_status in ("action_required", "linked_task"):
        action = True
        signals.append("prior_status_action")
    if any(n in blob for n in ACTION):
        action = True
        signals.append("action_keyword")
    if any(n in blob for n in QUESTION_CUES) and not is_noise:
        action = True
        signals.append("question_or_request")
    if any(n in blob for n in MONEY_CUES):
        signals.append("money")
        action = True
    if any(n in blob for n in SECURITY_CUES):
        signals.append("security")
        action = True
    if paperclip_issue_id:
        signals.append("linked_paperclip")

    if is_noise and not action:
        priority = "noise"
        intent = "Likely automated / marketing / newsletter — no Boss action."
        recommendation = "Mark ignored or archive; do not create Paperclip task."
        review_status = "ignored"
        questions: list[str] = []
    elif action:
        if "security" in signals:
            priority = "urgent"
        elif "money" in signals:
            priority = "high"
        else:
            priority = "high" if "urgent" in blob or "asap" in blob else "medium"
        intent = (
            f"Sender appears to request attention or a decision related to cell `{cell}`."
        )
        recommendation = (
            "Create or link a Paperclip issue; Hermes should ask Boss for desired outcome "
            "before agents act."
        )
        review_status = "needs_boss"
        questions = [
            f"What outcome do you want for: {subject[:80]}?",
            "Create/link a Paperclip task, reply draft only, or ignore?",
        ]
        if "money" in signals:
            questions.append("Is payment/invoice approved, or hold?")
        if "security" in signals:
            questions.append("Treat as security-sensitive — confirm before any click/reply?")
    else:
        priority = "low"
        intent = f"Informational message tagged to cell `{cell}` — no clear action cue."
        recommendation = "Triage as reviewed; monitor thread if reply arrives."
        review_status = "reviewed"
        questions = []

    preview = (snippet or body or "").strip().replace("\r", "")
    preview = re.sub(r"\n{3,}", "\n\n", preview)[:400]
    summary = (
        f"From {email or from_raw}: {subject[:120]}. "
        f"Cell={cell}; priority={priority}; action_required={action}."
    )

    received = ""
    if received_at is not None:
        try:
            received = received_at.isoformat()
        except Exception:
            received = str(received_at)

    report_lines = [
        f"## Email review — {subject[:120]}",
        "",
        f"- **Mailbox:** {mailbox}",
        f"- **Gmail id:** `{gmail_id}`",
        f"- **From:** {from_raw}",
        f"- **Received:** {received or 'unknown'}",
        f"- **Inbox:** {'yes' if is_inbox else 'no'}",
        f"- **Cell:** `{cell}`",
        f"- **Review status:** `{review_status}`",
        f"- **Priority:** `{priority}`",
        f"- **Action required:** {'yes' if action else 'no'}",
        f"- **Paperclip:** {paperclip_issue_id or 'unlinked'}",
        f"- **Signals:** {', '.join(signals) if signals else 'none'}",
        "",
        "### Intent",
        intent,
        "",
        "### Summary",
        summary,
        "",
        "### Recommendation",
        recommendation,
        "",
    ]
    if questions:
        report_lines.append("### Questions for Boss")
        for q in questions:
            report_lines.append(f"- {q}")
        report_lines.append("")
    report_lines.extend(
        [
            "### Preview",
            "```",
            preview or "(empty)",
            "```",
            "",
        ]
    )
    report_md = "\n".join(report_lines)

    return {
        "person_email": email,
        "business_slug": cell,
        "review_status": review_status,
        "priority": priority,
        "is_noise": is_noise and not action,
        "action_required": action,
        "intent": intent,
        "summary": summary,
        "recommendation": recommendation,
        "questions": questions,
        "signals": signals,
        "report_markdown": report_md,
        "analysis_json": {
            "cell": cell,
            "priority": priority,
            "action_required": action,
            "is_noise": is_noise and not action,
            "signals": signals,
            "questions": questions,
            "paperclip_issue_id": paperclip_issue_id,
            "from_email": email,
        },
    }


def ensure_person(cur, email: str, from_display: str, business_id) -> str | None:
    if not email:
        return None
    cur.execute(
        "SELECT id FROM ops.people WHERE lower(primary_email) = %s OR %s = ANY(emails) LIMIT 1",
        (email, email),
    )
    row = cur.fetchone()
    if row:
        return str(row["id"])
    name = from_display.strip() or email
    if "<" in (from_display or ""):
        name = parseaddr(from_display)[0].strip() or email
    cur.execute(
        """
        INSERT INTO ops.people (display_name, kind, primary_email, emails, primary_business_id, tags, notes)
        VALUES (%s, 'contact', %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            name[:200],
            email,
            [email],
            business_id,
            ["auto_from_gmail"],
            f"Auto-created from clawsums@gmail.com sender {email}",
        ),
    )
    return str(cur.fetchone()["id"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--inbox-only", action="store_true")
    ap.add_argument("--sync-first", action="store_true")
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument(
        "--per-email-report",
        action="store_true",
        default=True,
        help="Include every email's analysis in output (default on)",
    )
    ap.add_argument("--no-per-email-report", action="store_true")
    ap.add_argument("--report-dir", help="Write one .md file per email")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--create-reminders", action="store_true")
    args = ap.parse_args()
    per_email = args.per_email_report and not args.no_per_email_report

    env = load_env()
    mailbox = env.get("GMAIL_ADMIN_ADDRESS", "clawsums@gmail.com")

    if args.sync_first:
        sync = SCRIPTS / "gmail-sync.py"
        if sync.is_file():
            print("== gmail-sync ==", file=sys.stderr)
            subprocess.check_call([sys.executable, str(sync)])
        else:
            print("WARN: gmail-sync.py not found", file=sys.stderr)

    report_dir = Path(args.report_dir) if args.report_dir else None
    if report_dir and not args.dry_run:
        report_dir.mkdir(parents=True, exist_ok=True)

    conn = connect()
    summary: dict = {
        "mailbox": mailbox,
        "reviewed": 0,
        "action_items": [],
        "by_cell": {},
        "by_priority": {},
        "by_status": {},
        "new_people": 0,
        "tasks_created": 0,
        "reminders_created": 0,
        "questions_for_boss": [],
        "email_reports": [],
    }

    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, slug FROM ops.businesses WHERE active")
            biz_by_slug = {r["slug"]: r["id"] for r in cur.fetchall()}

            where = ["1=1"]
            params: list = []
            if not args.all:
                where.append(
                    "(review_status IS NULL OR review_status = 'unreviewed' "
                    "OR analysis_report IS NULL)"
                )
            if args.inbox_only:
                where.append("is_inbox = true")
            where.append("(mailbox IS NULL OR mailbox = %s OR mailbox = 'clawsums@gmail.com')")
            params.append(mailbox)

            sql = f"""
                SELECT id, gmail_id, from_addr, subject, snippet, body_text,
                       processing_status, domain_guess, paperclip_issue_id,
                       is_inbox, received_at
                FROM ops.emails
                WHERE {' AND '.join(where)}
                ORDER BY received_at DESC NULLS LAST
                LIMIT %s
            """
            params.append(args.limit)
            cur.execute(sql, params)
            rows = cur.fetchall()

            for row in rows:
                subject = row["subject"] or "(no subject)"
                body = (row["body_text"] or row["snippet"] or "")[:5000]
                from_raw = row["from_addr"] or ""
                analysis = analyze_email(
                    subject=subject,
                    from_raw=from_raw,
                    body=body,
                    snippet=row.get("snippet") or "",
                    processing_status=row.get("processing_status") or "",
                    domain_guess=row.get("domain_guess"),
                    paperclip_issue_id=row.get("paperclip_issue_id"),
                    is_inbox=bool(row.get("is_inbox")),
                    gmail_id=row["gmail_id"],
                    received_at=row.get("received_at"),
                    mailbox=mailbox,
                )
                cell_slug = analysis["business_slug"]
                business_id = biz_by_slug.get(cell_slug)
                email = analysis["person_email"]
                action = analysis["action_required"]
                review_status = analysis["review_status"]

                person_id = None
                if email and not args.dry_run:
                    cur.execute(
                        "SELECT id FROM ops.people WHERE lower(primary_email) = %s LIMIT 1",
                        (email,),
                    )
                    existed = cur.fetchone()
                    person_id = ensure_person(cur, email, from_raw, business_id)
                    if not existed:
                        summary["new_people"] += 1

                for q in analysis["questions"]:
                    if q not in summary["questions_for_boss"] and len(summary["questions_for_boss"]) < 20:
                        summary["questions_for_boss"].append(q)

                task_id = None
                if action and not args.dry_run:
                    cur.execute(
                        """
                        SELECT id FROM ops.tasks
                        WHERE source = 'gmail' AND source_ref = %s
                        LIMIT 1
                        """,
                        (row["gmail_id"],),
                    )
                    existing_task = cur.fetchone()
                    if existing_task:
                        task_id = existing_task["id"]
                    else:
                        cur.execute(
                            """
                            INSERT INTO ops.tasks (
                              title, description, status, priority, business_id, person_id,
                              source, source_ref, email_id, paperclip_issue_id, assigned_agent,
                              clarification_questions, tags
                            ) VALUES (
                              %s, %s, 'pending', %s, %s, %s::uuid,
                              'gmail', %s, %s, %s, %s,
                              %s, %s
                            )
                            RETURNING id
                            """,
                            (
                                f"Email: {subject[:160]}",
                                analysis["report_markdown"][:8000],
                                "high" if analysis["priority"] in ("high", "urgent") else "medium",
                                business_id,
                                person_id,
                                row["gmail_id"],
                                row["id"],
                                row.get("paperclip_issue_id"),
                                cell_slug,
                                analysis["questions"]
                                or [
                                    "What is the desired outcome?",
                                    "Create or link a Paperclip issue?",
                                ],
                                ["gmail", "inbox_review", cell_slug, analysis["priority"]],
                            ),
                        )
                        task_id = cur.fetchone()["id"]
                        summary["tasks_created"] += 1

                    if args.create_reminders:
                        cur.execute(
                            """
                            INSERT INTO ops.reminders (
                              title, description, due_date, remind_daily, priority,
                              source, source_ref, gmail_id, business_id, person_id, task_id
                            )
                            SELECT %s, %s, CURRENT_DATE, true, %s,
                                   'gmail', %s, %s, %s, %s::uuid, %s
                            WHERE NOT EXISTS (
                              SELECT 1 FROM ops.reminders
                              WHERE gmail_id = %s AND completed_at IS NULL
                            )
                            """,
                            (
                                f"Follow up: {subject[:100]}",
                                analysis["summary"],
                                "urgent" if analysis["priority"] == "urgent" else "high",
                                row["gmail_id"],
                                row["gmail_id"],
                                business_id,
                                person_id,
                                task_id,
                                row["gmail_id"],
                            ),
                        )
                        if cur.rowcount:
                            summary["reminders_created"] += 1

                if not args.dry_run:
                    cur.execute(
                        """
                        UPDATE ops.emails SET
                          mailbox = COALESCE(mailbox, %s),
                          business_id = %s,
                          person_id = COALESCE(%s::uuid, person_id),
                          review_status = %s,
                          review_notes = %s,
                          reviewed_at = now(),
                          analysis_summary = %s,
                          analysis_intent = %s,
                          analysis_recommendation = %s,
                          analysis_priority = %s,
                          analysis_json = %s,
                          analysis_report = %s,
                          processing_status = CASE
                            WHEN %s AND processing_status IN ('pending', 'triaged') THEN 'action_required'
                            WHEN processing_status = 'pending' AND %s THEN 'ignored'
                            WHEN processing_status = 'pending' THEN 'triaged'
                            ELSE processing_status
                          END,
                          domain_guess = COALESCE(domain_guess, %s)
                        WHERE id = %s
                        """,
                        (
                            mailbox,
                            business_id,
                            person_id,
                            review_status,
                            f"cell={cell_slug}; priority={analysis['priority']}; action={action}",
                            analysis["summary"],
                            analysis["intent"],
                            analysis["recommendation"],
                            analysis["priority"],
                            json.dumps(analysis["analysis_json"]),
                            analysis["report_markdown"],
                            action,
                            analysis["is_noise"],
                            cell_slug,
                            row["id"],
                        ),
                    )
                    cur.execute(
                        """
                        INSERT INTO ops.email_reviews (
                          email_id, gmail_id, mailbox, business_slug, person_email,
                          review_status, priority, is_noise, action_required,
                          intent, summary, recommendation, questions, signals,
                          linked_task_id, report_markdown, analysis_json, analyzed_at
                        ) VALUES (
                          %s, %s, %s, %s, %s,
                          %s, %s, %s, %s,
                          %s, %s, %s, %s, %s,
                          %s, %s, %s, now()
                        )
                        ON CONFLICT (email_id) DO UPDATE SET
                          business_slug = EXCLUDED.business_slug,
                          person_email = EXCLUDED.person_email,
                          review_status = EXCLUDED.review_status,
                          priority = EXCLUDED.priority,
                          is_noise = EXCLUDED.is_noise,
                          action_required = EXCLUDED.action_required,
                          intent = EXCLUDED.intent,
                          summary = EXCLUDED.summary,
                          recommendation = EXCLUDED.recommendation,
                          questions = EXCLUDED.questions,
                          signals = EXCLUDED.signals,
                          linked_task_id = COALESCE(EXCLUDED.linked_task_id, ops.email_reviews.linked_task_id),
                          report_markdown = EXCLUDED.report_markdown,
                          analysis_json = EXCLUDED.analysis_json,
                          analyzed_at = now()
                        """,
                        (
                            row["id"],
                            row["gmail_id"],
                            mailbox,
                            cell_slug,
                            email,
                            review_status,
                            analysis["priority"],
                            analysis["is_noise"],
                            action,
                            analysis["intent"],
                            analysis["summary"],
                            analysis["recommendation"],
                            analysis["questions"],
                            analysis["signals"],
                            task_id,
                            analysis["report_markdown"],
                            json.dumps(analysis["analysis_json"]),
                        ),
                    )

                if report_dir and not args.dry_run:
                    safe = re.sub(r"[^\w.-]+", "_", row["gmail_id"])[:80]
                    (report_dir / f"{safe}.md").write_text(
                        analysis["report_markdown"], encoding="utf-8"
                    )

                entry = {
                    "email_id": row["id"],
                    "gmail_id": row["gmail_id"],
                    "subject": subject[:160],
                    "from": email or from_raw,
                    "cell": cell_slug,
                    "review_status": review_status,
                    "priority": analysis["priority"],
                    "action_required": action,
                    "intent": analysis["intent"],
                    "summary": analysis["summary"],
                    "recommendation": analysis["recommendation"],
                    "questions": analysis["questions"],
                    "signals": analysis["signals"],
                    "report_markdown": analysis["report_markdown"],
                    "received_at": row["received_at"].isoformat()
                    if row.get("received_at")
                    else None,
                }
                if per_email:
                    summary["email_reports"].append(entry)

                summary["reviewed"] += 1
                summary["by_cell"][cell_slug] = summary["by_cell"].get(cell_slug, 0) + 1
                summary["by_priority"][analysis["priority"]] = (
                    summary["by_priority"].get(analysis["priority"], 0) + 1
                )
                st = row.get("processing_status") or "pending"
                summary["by_status"][st] = summary["by_status"].get(st, 0) + 1
                if action:
                    summary["action_items"].append(
                        {
                            "subject": subject[:120],
                            "from": email or from_raw,
                            "cell": cell_slug,
                            "priority": analysis["priority"],
                            "gmail_id": row["gmail_id"],
                            "received_at": entry["received_at"],
                        }
                    )

            cur.execute(
                "SELECT review_status, count(*) AS n FROM ops.emails GROUP BY 1"
            )
            summary["review_totals"] = {
                r["review_status"]: r["n"] for r in cur.fetchall()
            }
            cur.execute(
                "SELECT count(*) AS n FROM ops.emails WHERE is_inbox AND processing_status = 'pending'"
            )
            summary["inbox_pending"] = int(cur.fetchone()["n"])
            cur.execute("SELECT count(*) AS n FROM ops.email_reviews")
            summary["email_reviews_stored"] = int(cur.fetchone()["n"])

    if args.markdown:
        lines = [
            f"# Inbox review — {mailbox}",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Reviewed this pass: **{summary['reviewed']}**",
            f"Per-email reports stored: **{summary.get('email_reviews_stored', 'n/a')}**",
            f"Action items: **{len(summary['action_items'])}**",
            f"New people: {summary['new_people']} · Tasks: {summary['tasks_created']} · Reminders: {summary['reminders_created']}",
            "",
            "## By cell",
        ]
        for k, v in sorted(summary["by_cell"].items(), key=lambda x: -x[1]):
            lines.append(f"- {k}: {v}")
        lines += ["", "## By priority"]
        for k, v in sorted(summary["by_priority"].items(), key=lambda x: -x[1]):
            lines.append(f"- {k}: {v}")
        lines += ["", "## Ask Boss"]
        for q in summary["questions_for_boss"] or ["(none)"]:
            lines.append(f"- {q}")
        if per_email:
            lines += ["", "# Per-email analysis", ""]
            for i, rep in enumerate(summary["email_reports"], 1):
                lines.append(f"---")
                lines.append(f"### {i}. {rep['subject']}")
                lines.append("")
                lines.append(rep["report_markdown"])
        else:
            lines += ["", "## Action items"]
            for a in summary["action_items"][:25]:
                lines.append(
                    f"- [{a['priority']}/{a['cell']}] {a['from']} — {a['subject']}"
                )
        sys.stdout.write("\n".join(lines) + "\n")
    else:
        print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
