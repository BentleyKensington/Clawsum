#!/usr/bin/env python3
"""
Strategic GHL CRM audit — automations, fields, conversations, re-engage list.

Generic by default (any GHL sub-account). Optional REI vertical heuristics via --vertical rei.

Usage:
  python3 ghl-strategic-audit.py --slug ghl
  python3 ghl-strategic-audit.py --slug ghl --contact-limit 400 --conversation-limit 150
  python3 ghl-strategic-audit.py --slug ghl --use-llm
  python3 ghl-strategic-audit.py --slug ghl --vertical rei   # instance overlay only
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.request
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
    sql_quote,
    sync_db_password,
)

ROOT = Path("/docker/clawsum")
OBS = ROOT / "obsidian"
ENV_FILE = ROOT / ".env"
STRATEGIC_SQL = ROOT / "postgres-init" / "09-ghl-strategic-tables.sql"
SMS_SQL = ROOT / "postgres-init" / "10-ghl-suggested-sms.sql"
COACHING_SQL = ROOT / "postgres-init" / "11-ghl-coaching-columns.sql"
AUDIT_SQL = ROOT / "postgres-init" / "08-ghl-audit-tables.sql"
TZ = ZoneInfo("America/Chicago")

VERTICAL_GENERIC = "generic"
VERTICAL_REI = "rei"

# Generic CRM field patterns (default)
GENERIC_FIELD_PATTERNS = [
    ("lead_source", r"lead.?source|source|campaign|utm|channel"),
    ("lifecycle_stage", r"stage|status|pipeline|lifecycle"),
    ("owner_assigned", r"owner|assigned|rep|agent|user"),
    ("next_action", r"next.?step|follow.?up|task|reminder"),
    ("deal_value", r"value|amount|revenue|budget|deal.?size"),
    ("contact_notes", r"notes|summary|description|comments"),
]

# REI vertical (optional --vertical rei)
REI_FIELD_PATTERNS = [
    ("property_address", r"property.?address|street.?address|subject.?property|address"),
    ("motivation", r"motivation|reason.?for.?sell|why.?sell|seller.?motivation"),
    ("timeline", r"timeline|timeframe|close.?date|when.?sell|urgency"),
    ("condition", r"condition|repairs|property.?condition"),
    ("asking_price", r"asking|price|offer.?amount|desired.?price|arv"),
    ("lead_source", r"lead.?source|source|campaign|utm"),
    ("beds_baths", r"bed|bath|sqft|square|bedroom"),
    ("equity", r"equity|mortgage|owed|lien"),
    ("appointment", r"appointment|appt|visit|walkthrough"),
    ("deal_type", r"deal.?type|strategy|wholesale|assignment"),
]

SELLER_PIPELINE_HINTS = re.compile(
    r"seller|sell|motivat|distress|probate|lead|cold.?outreach|referr|real.?seller",
    re.I,
)
BUYER_PIPELINE_HINTS = re.compile(r"buyer|cash.?buyer|disposition|contract|wholesale.?buy", re.I)

# Lead intent / viability (SMS + call transcripts)
INTENT_NON_VIABLE = "non_viable"
INTENT_REFERRAL_LOW = "referral_low_intent"
INTENT_BONAFIDE_SELLER = "bonafide_seller"
INTENT_BONAFIDE_REFERRAL = "bonafide_referral"
INTENT_UNCLEAR = "unclear"

NON_VIABLE_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\bjust (?:thinking|considering|wondering|browsing)\b",
        r"\bmight (?:have|be)\b",
        r"\bnot (?:sure|ready|interested|selling|a seller)\b",
        r"\bwrong number\b",
        r"\b(?:stop|unsubscribe|remove me|do not call|don't call)\b",
        r"\bno (?:rush|hurry|timeline|pressure)\b",
        r"\bjust curious\b",
        r"\btire kicker\b",
        r"\bnot serious\b",
        r"\bmaybe (?:later|someday|eventually)\b",
    )
]
REFERRAL_LOW_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\b(?:considering|thinking about) referr(?:ing|al)\b",
        r"\brefer(?:ring|ral)? (?:a |someone(?:'s)? )\b",
        r"\bknow someone\b",
        r"\bfriend(?:'s| has| who)\b",
        r"\bneighbor\b",
        r"\bnot (?:my|mine)\b.*\b(?:house|property|home)\b",
        r"\bsomeone else(?:'s)?\b.*\b(?:house|property|sell)\b",
        r"\bclient (?:who|that) (?:might|may)\b",
        r"\bmight refer\b",
    )
]
SELLER_INTEREST_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\b(?:I|we) (?:want|need|are looking) to sell\b",
        r"\b(?:I|we)(?:'m| are) selling\b",
        r"\bselling (?:my|the|this|our)\b",
        r"\b(?:my|our) (?:house|property|home|rental)\b",
        r"\bcash offer\b",
        r"\bwhen can you (?:come|visit|see|look)\b",
        r"\bappointment\b|\bwalkthrough\b",
        r"\bmotivat",
        r"\bdivorce\b|\bprobate\b|\binherited\b|\bvacant\b|\bforeclosure\b",
        r"\bhow much (?:would you|can you) (?:pay|offer)\b",
        r"\baddress is\b|\bat \d+\s+\w+",
        r"\b(?:I|we) (?:need|want) (?:an )?offer\b",
        r"\bready to (?:sell|move|close)\b",
    )
]
DIRECT_OWNER_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\b(?:I|we) (?:want|need|are looking) to sell\b",
        r"\b(?:my|our) (?:house|property|home|rental)\b",
        r"\bselling (?:my|our)\b",
    )
]
REFERRAL_SERIOUS_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\b(?:seller|owner) (?:wants|needs|looking) to sell\b",
        r"\b(?:has|have) (?:a )?property (?:to sell|for sale)\b",
        r"\bwill (?:send|give|introduce|connect)\b",
        r"\bdefinitely\b.*\brefer\b",
        r"\bhot lead\b.*\brefer\b",
    )
]

FOLLOWUP_REPLY_SLA = timedelta(hours=48)
RECENT_OUTBOUND_WINDOW = timedelta(days=7)

LANDLINE_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\blandline\b",
        r"\bnumber is a landline\b",
        r"\bcannot receive sms\b",
        r"\bcan't receive (?:sms|text)",
        r"\bnot a mobile\b",
        r"\bnon[- ]?mobile\b",
        r"\bsms (?:not|isn't|cannot be) (?:supported|available|delivered)",
        r"\bunable to deliver\b",
        r"\bmessage failed\b",
        r"\bdelivery failed\b",
        r"\b30006\b",
        r"\blandline detected\b",
        r"\btext messaging.*not available\b",
    )
]

# Our drip / qualify scripts — never treat as unanswered inbound seller questions
OUR_OUTBOUND_SCRIPT_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"what(?:'s| is) your (?:first )?name",
        r"before we dive in",
        r"did i catch you at a bad time",
        r"hey there",
        r"still (?:looking|interested) (?:to sell|in selling)",
        r"are you still (?:looking|considering)",
        r"just checking in",
        r"this isn't something you're looking into",
    )
]

DISPOSITION_LANDLINE = "landline_no_sms"
DISPOSITION_MOVE_ON = "move_on"
DISPOSITION_OUTBOUND_ONLY = "outbound_only_no_response"
GHL_LANDLINE_TAGS = ["landline", "no-sms"]


def parse_ts(val: Any) -> datetime | None:
    if not val:
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(val / 1000 if val > 1e12 else val, tz=timezone.utc)
        except (OSError, ValueError):
            return None
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def ensure_tables() -> None:
    import subprocess

    for sql in (AUDIT_SQL, STRATEGIC_SQL, SMS_SQL, COACHING_SQL):
        p = sql if sql.exists() else Path(__file__).resolve().parent.parent / "postgres-init" / sql.name
        if p.exists():
            subprocess.run(
                [
                    "docker", "exec", "-i", "clawsum-postgres-1", "psql",
                    "-U", "clawsum", "-d", "ghl", "-v", "ON_ERROR_STOP=1",
                ],
                input=p.read_bytes(),
                check=True,
            )


def fetch_contacts_recent(
    pit: str, loc: str, available: set[str], limit: int
) -> list[dict[str, Any]]:
    """Fetch contacts; sort newest-first client-side."""
    by_id: dict[str, dict[str, Any]] = {}
    page_variants = [
        {"limit": 100},
        {"limit": 100, "page": 1},
        {"limit": 100, "page": 2},
        {"limit": 100, "page": 3},
        {"limit": 100, "page": 4},
        {"limit": 100, "page": 5},
    ]
    for params in page_variants:
        data = mcp_tool("contacts_get-contacts", params, pit, loc, available, compact_limit=str(limit))
        if isinstance(data, dict) and data.get("_error"):
            continue
        contacts = (data or {}).get("contacts") if isinstance(data, dict) else []
        if not contacts:
            continue
        for c in contacts:
            if isinstance(c, dict) and c.get("id"):
                by_id[c["id"]] = c
        if len(by_id) >= limit:
            break

    contacts = list(by_id.values())
    contacts.sort(
        key=lambda c: parse_ts(c.get("dateAdded") or c.get("lastActivity")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return contacts[:limit]


def fetch_pipelines(pit: str, loc: str, available: set[str]) -> list[dict[str, Any]]:
    data = mcp_tool("opportunities_get-pipelines", {}, pit, loc, available)
    if isinstance(data, dict):
        return data.get("pipelines") or []
    return []


def fetch_custom_fields(pit: str, loc: str, available: set[str]) -> list[dict[str, Any]]:
    data = mcp_tool("locations_get-custom-fields", {}, pit, loc, available)
    if isinstance(data, dict):
        return data.get("customFields") or []
    return []


def fetch_opportunities(pit: str, loc: str, available: set[str], limit: int) -> list[dict[str, Any]]:
    data = mcp_tool("opportunities_search-opportunity", {"limit": limit}, pit, loc, available, compact_limit=str(limit))
    opps = (data or {}).get("opportunities") if isinstance(data, dict) else []
    opps = opps or []
    opps.sort(
        key=lambda o: parse_ts(o.get("updatedAt") or o.get("createdAt")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return opps[:limit]


def fetch_conversations(pit: str, loc: str, available: set[str], limit: int) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for page in range(1, max(2, (limit // 100) + 2)):
        data = mcp_tool(
            "conversations_search-conversation",
            {"limit": 100, "page": page},
            pit,
            loc,
            available,
            compact_limit=str(limit),
        )
        convs = (data or {}).get("conversations") if isinstance(data, dict) else []
        if not convs:
            break
        for c in convs:
            if isinstance(c, dict) and c.get("id"):
                by_id[c["id"]] = c
        if len(by_id) >= limit:
            break
    convs = list(by_id.values())
    convs.sort(
        key=lambda c: parse_ts(c.get("lastMessageDate")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return convs[:limit]


def fetch_messages(pit: str, loc: str, available: set[str], conversation_id: str) -> list[dict[str, Any]]:
    if "conversations_get-messages" not in available:
        return []
    for params in (
        {"conversationId": conversation_id},
        {"conversation_id": conversation_id},
        {"id": conversation_id},
    ):
        data = mcp_tool("conversations_get-messages", params, pit, loc, available, compact_limit="200")
        if isinstance(data, dict) and data.get("messages"):
            msgs = data["messages"]
            msgs.sort(key=lambda m: parse_ts(m.get("dateAdded")) or datetime.min.replace(tzinfo=timezone.utc))
            return msgs
    return []


def field_patterns(vertical: str) -> list[tuple[str, str]]:
    return REI_FIELD_PATTERNS if vertical == VERTICAL_REI else GENERIC_FIELD_PATTERNS


def match_fields(fields: list[dict[str, Any]], vertical: str) -> dict[str, list[str]]:
    patterns = field_patterns(vertical)
    matched: dict[str, list[str]] = {k: [] for k, _ in patterns}
    for f in fields:
        label = " ".join(
            str(f.get(k) or "") for k in ("name", "fieldKey", "label", "placeholder")
        ).lower()
        for key, pattern in patterns:
            if re.search(pattern, label, re.I):
                matched[key].append(f.get("name") or f.get("fieldKey") or "?")
    return matched


def match_rei_fields(fields: list[dict[str, Any]]) -> dict[str, list[str]]:
    return match_fields(fields, VERTICAL_REI)


def analyze_fields(fields: list[dict[str, Any]], vertical: str = VERTICAL_GENERIC) -> tuple[list[dict[str, str]], list[str]]:
    matched = match_fields(fields, vertical)
    recommendations: list[dict[str, str]] = []
    missing: list[str] = []
    if vertical == VERTICAL_REI:
        essential = ["property_address", "motivation", "timeline", "condition", "asking_price", "lead_source"]
        for key in essential:
            if not matched.get(key):
                missing.append(key)
                recommendations.append(
                    {
                        "area": "custom_fields",
                        "priority": "high",
                        "issue": f"Missing REI essential field: {key.replace('_', ' ')}",
                        "fix": f"Create custom field for {key.replace('_', ' ')}; require on lead forms; add to rep view.",
                    }
                )
        if len(matched.get("motivation", [])) > 1:
            recommendations.append(
                {
                    "area": "custom_fields",
                    "priority": "medium",
                    "issue": "Duplicate motivation-style fields",
                    "fix": "Consolidate to one canonical motivation field; migrate data; remove duplicates.",
                }
            )
        return recommendations, missing

    essential = ["lead_source", "lifecycle_stage", "owner_assigned"]
    for key in essential:
        if not matched.get(key):
            missing.append(key)
            recommendations.append(
                {
                    "area": "custom_fields",
                    "priority": "medium",
                    "issue": f"Missing CRM field category: {key.replace('_', ' ')}",
                    "fix": f"Add or rename a custom field for {key.replace('_', ' ')}; surface on contact record and reports.",
                }
            )
    return recommendations, missing


def analyze_pipelines(pipelines: list[dict[str, Any]], vertical: str = VERTICAL_GENERIC) -> tuple[list[dict[str, str]], dict[str, str]]:
    recs: list[dict[str, str]] = []
    stage_map: dict[str, str] = {}
    for p in pipelines:
        for s in p.get("stages") or []:
            if s.get("id"):
                stage_map[s["id"]] = f"{p.get('name', '?')} → {s.get('name', '?')}"

    if vertical == VERTICAL_GENERIC:
        if len(pipelines) > 6:
            recs.append(
                {
                    "area": "pipelines",
                    "priority": "medium",
                    "issue": f"{len(pipelines)} pipelines — high operational complexity",
                    "fix": "Archive inactive pipelines; consolidate stages; document one primary lead-to-close path.",
                }
            )
        for p in pipelines:
            if not (p.get("stages") or []):
                recs.append(
                    {
                        "area": "pipelines",
                        "priority": "low",
                        "issue": f"Pipeline '{p.get('name')}' has no stages",
                        "fix": "Add stages or archive unused pipeline.",
                    }
                )
        return recs, stage_map

    seller_pipes = []
    buyer_pipes = []
    for p in pipelines:
        name = p.get("name") or ""
        if SELLER_PIPELINE_HINTS.search(name):
            seller_pipes.append(name)
        elif BUYER_PIPELINE_HINTS.search(name):
            buyer_pipes.append(name)
        for s in p.get("stages") or []:
            if s.get("id"):
                stage_map[s["id"]] = f"{name} → {s.get('name', '?')}"

    if len(pipelines) > 5:
        recs.append(
            {
                "area": "pipelines",
                "priority": "high",
                "issue": f"{len(pipelines)} pipelines — high complexity for REI seller conversion",
                "fix": "Consolidate to 2–3 seller-acquisition pipelines (Lead → Contacted → Appt → Offer → Contract → Dead). "
                "Move buyer/disposition to separate pipeline. Archive unused 2023 workflow pipelines if inactive.",
            }
        )
    if not seller_pipes:
        recs.append(
            {
                "area": "pipelines",
                "priority": "critical",
                "issue": "No clearly named seller-acquisition pipeline detected",
                "fix": "Create 'Seller Acquisition' pipeline with stages: New Lead → Contacted → Appointment Set → "
                "Offer Made → Under Contract → Closed / Dead.",
            }
        )
    if seller_pipes and buyer_pipes:
        recs.append(
            {
                "area": "pipelines",
                "priority": "info",
                "issue": f"Seller pipelines: {', '.join(seller_pipes[:4])}; Buyer/disposition: {', '.join(buyer_pipes[:4])}",
                "fix": "Ensure automations route seller leads ONLY into seller pipelines; never mix buyer nurture on seller tags.",
            }
        )
    # Stage hygiene
    for p in pipelines:
        stages = p.get("stages") or []
        names = [s.get("name", "").lower() for s in stages]
        if "appointment" not in " ".join(names) and SELLER_PIPELINE_HINTS.search(p.get("name") or ""):
            recs.append(
                {
                    "area": "pipelines",
                    "priority": "medium",
                    "issue": f"Pipeline '{p.get('name')}' lacks explicit appointment stage",
                    "fix": "Add 'Appointment Set' stage between contact and offer for speed-to-lead tracking.",
                }
            )
    return recs, stage_map


def automation_recommendations(conversation_flags: int, stale_recent: int, vertical: str = VERTICAL_GENERIC) -> list[dict[str, str]]:
    recs = [
        {
            "area": "automations",
            "priority": "critical",
            "issue": "Workflow inventory not exposed via GHL MCP API",
            "fix": "Manual GHL audit required: Settings → Automations. Verify: (1) missed-call text-back <2min, "
            "(2) new-lead instant SMS, (3) no-reply in 24h task for assigned user, (4) 7/14/30-day stale nurture, "
            "(5) appointment no-show sequence.",
        },
    ]
    if conversation_flags > 5:
        follow_fix = (
            "Add/update workflow: trigger on inbound message → wait 5min → if no outbound, send scripted "
            "reply + create task + notify assigned rep. Target first response in <15 minutes."
        )
        if vertical == VERTICAL_REI:
            follow_fix = (
                "Add/update workflow: trigger on inbound SMS/call → wait 5min → if no outbound, send scripted "
                "SMS + create task + notify acquisitions rep. REI standard: respond in <5 minutes."
            )
        recs.append(
            {
                "area": "automations",
                "priority": "critical",
                "issue": f"{conversation_flags} conversations with inbound not followed up promptly",
                "fix": follow_fix,
            }
        )
    if stale_recent > 10:
        stale_fix = (
            "Deploy re-engagement workflow: Day 1 touch, Day 3 value-add, Day 7 check-in with opt-out. "
            "Tag for quarterly re-engage review."
        )
        if vertical == VERTICAL_REI:
            stale_fix = (
                "Deploy re-engagement workflow: Day 1 SMS + call, Day 3 value-add, Day 7 'still looking to sell?' "
                "with opt-out. Tag 'Re-engage-Q{quarter}'."
            )
        recs.append(
            {
                "area": "automations",
                "priority": "high",
                "issue": f"{stale_recent} recent leads (30d) with no meaningful follow-up",
                "fix": stale_fix,
            }
        )
    speed_issue = "Speed-to-lead strongly affects conversion"
    speed_fix = (
        "Ensure: new form lead → instant auto-reply → assigned rep notified → pipeline stage set → "
        "no-reply escalation within 24h."
    )
    if vertical == VERTICAL_REI:
        speed_issue = "Speed-to-lead is the #1 REI conversion lever"
        speed_fix = (
            "Ensure: new Facebook/web form lead → instant SMS (human tone) → round-robin call within 5min → "
            "if no answer, voicemail drop + SMS 'just tried you' → pipeline stage 'New Lead' auto-set."
        )
    recs.append(
        {
            "area": "automations",
            "priority": "high",
            "issue": speed_issue,
            "fix": speed_fix,
        }
    )
    return recs


def _pattern_hits(text: str, patterns: list[re.Pattern[str]]) -> list[str]:
    return [p.pattern for p in patterns if p.search(text)]


def classify_lead_intent(text: str) -> dict[str, Any]:
    """Classify seller vs referral vs non-viable from SMS/call transcript text."""
    blob = (text or "").strip()
    if not blob:
        return {
            "intent": INTENT_UNCLEAR,
            "viability": "unclear",
            "confidence": "low",
            "signals": {},
            "summary": "No transcript text available",
        }

    signals = {
        "non_viable": _pattern_hits(blob, NON_VIABLE_PATTERNS),
        "referral_low": _pattern_hits(blob, REFERRAL_LOW_PATTERNS),
        "seller": _pattern_hits(blob, SELLER_INTEREST_PATTERNS),
        "referral_serious": _pattern_hits(blob, REFERRAL_SERIOUS_PATTERNS),
        "direct_owner": _pattern_hits(blob, DIRECT_OWNER_PATTERNS),
    }
    has_seller = bool(signals["seller"])
    has_direct_owner = bool(signals["direct_owner"])
    has_ref_low = bool(signals["referral_low"])
    has_ref_serious = bool(signals["referral_serious"])
    has_non_viable = bool(signals["non_viable"])

    if has_direct_owner and not has_non_viable:
        intent = INTENT_BONAFIDE_SELLER
        viability = "viable"
        confidence = "high" if len(signals["direct_owner"]) >= 2 else "medium"
        summary = "Bonafide direct seller interest detected in transcript"
    elif has_seller and not has_ref_low and not has_non_viable:
        intent = INTENT_BONAFIDE_SELLER
        viability = "viable"
        confidence = "medium"
        summary = "Seller interest detected in transcript"
    elif has_ref_serious and not has_non_viable:
        intent = INTENT_BONAFIDE_REFERRAL
        viability = "viable"
        confidence = "medium"
        summary = "Serious referral opportunity — property owner may sell; nurture referrer for intro"
    elif has_ref_low and not has_direct_owner:
        intent = INTENT_REFERRAL_LOW
        viability = "non_viable"
        confidence = "high" if has_non_viable else "medium"
        summary = "Referral-only / low intent — considering referring, not a direct motivated seller"
    elif has_non_viable and not has_seller:
        intent = INTENT_NON_VIABLE
        viability = "non_viable"
        confidence = "high" if len(signals["non_viable"]) >= 2 else "medium"
        summary = "Non-viable — low motivation or disinterest signals in transcript"
    elif has_ref_low and has_seller:
        intent = INTENT_REFERRAL_LOW
        viability = "non_viable"
        confidence = "medium"
        summary = "Referral context — third-party property mentioned; not direct seller"
    else:
        intent = INTENT_UNCLEAR
        viability = "unclear"
        confidence = "low"
        summary = "Intent unclear from transcript — qualify before re-engage"

    return {
        "intent": intent,
        "viability": viability,
        "confidence": confidence,
        "signals": signals,
        "summary": summary,
    }


def message_direction(m: dict[str, Any]) -> str:
    direction = (m.get("direction") or "").lower()
    mtype = (m.get("type") or "").lower()
    if direction in ("outbound", "outgoing"):
        return "outbound"
    if direction in ("inbound", "incoming"):
        return "inbound"
    if "outbound" in mtype:
        return "outbound"
    if "inbound" in mtype or "incoming" in mtype:
        return "inbound"
    # Calls/voicemail without direction: infer from status if present
    status = (m.get("status") or m.get("messageStatus") or "").lower()
    if "failed" in status or "undelivered" in status:
        return "outbound"
    return ""


def is_our_outbound_script(text: str) -> bool:
    return bool(text and any(p.search(text) for p in OUR_OUTBOUND_SCRIPT_PATTERNS))


def detect_landline(
    text: str, contact: dict[str, Any] | None = None
) -> tuple[bool, str]:
    blob = text or ""
    tags = contact.get("tags") if contact else None
    tag_str = ", ".join(tags).lower() if isinstance(tags, list) else str(tags or "").lower()
    if any(t in tag_str for t in ("landline", "no-sms", "no sms", "land line")):
        return True, "Contact already tagged landline/no-sms in GHL"
    for pat in LANDLINE_PATTERNS:
        m = pat.search(blob)
        if m:
            return True, f"Landline/SMS failure signal: {m.group(0)[:60]}"
    return False, ""


def enrich_profile_disposition(
    profile: dict[str, Any], contact: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Annotate landline, outbound-only threads, and move-on dispositions."""
    transcript = profile.get("transcript_excerpt") or ""
    inbounds: list[str] = list(profile.get("inbound_bodies") or [])
    outbounds: list[str] = list(profile.get("outbound_bodies") or [])
    inbound_count = profile.get("inbound_count") or 0
    outbound_count = profile.get("outbound_count") or 0

    # Drop script lines mis-parsed as inbound (our drip questions)
    inbounds = [
        b
        for b in inbounds
        if not (is_our_outbound_script(b) and any(b[:50] in ob for ob in outbounds))
    ]
    profile["inbound_bodies"] = inbounds
    if len(inbounds) != inbound_count:
        profile["inbound_count"] = len(inbounds)
        inbound_count = len(inbounds)
        if inbounds:
            profile["last_inbound_at"] = profile.get("last_inbound_at")
        else:
            profile["last_inbound_at"] = None

    all_text = " ".join([transcript, *inbounds, *outbounds])
    landline, landline_reason = detect_landline(all_text, contact)

    if landline:
        profile.update(
            {
                "landline": True,
                "disposition": DISPOSITION_LANDLINE,
                "disposition_note": (
                    f"Landline detected — number cannot receive SMS. {landline_reason} "
                    "No response after our outbound is expected; use call only or remove from SMS re-engage."
                ),
                "ghl_tags_recommended": list(GHL_LANDLINE_TAGS),
                "followup_gap": False,
                "followup_gap_reason": None,
                "worked_lead": True,
                "intent": INTENT_NON_VIABLE,
                "viability": "non_viable",
                "intent_summary": "Landline — SMS re-engage not viable",
            }
        )
        return profile

    if inbound_count == 0 and outbound_count > 0:
        last_out = (outbounds[-1] if outbounds else "")[:80]
        profile.update(
            {
                "disposition": DISPOSITION_OUTBOUND_ONLY,
                "disposition_note": (
                    "Outbound-only thread — we sent SMS (e.g. qualify/drip) but zero inbound replies. "
                    f"Last outbound: {last_out!r}. "
                    "Likely landline — number cannot receive SMS; tag `landline` in GHL and use call-only or move on."
                ),
                "ghl_tags_recommended": ["landline", "no-sms"],
                "followup_gap": False,
                "followup_gap_reason": None,
                "worked_lead": True,
                "intent": INTENT_NON_VIABLE,
                "viability": "non_viable",
                "intent_summary": "No inbound engagement — not a missed SMS follow-up",
            }
        )
        return profile

    intent = profile.get("intent")
    if intent in (INTENT_REFERRAL_LOW, INTENT_NON_VIABLE):
        note = profile.get("intent_summary") or "Non-viable — move on"
        if profile.get("worked_lead") or outbound_count > 0:
            note += "; already worked via outbound — do not re-engage"
        profile.update(
            {
                "disposition": DISPOSITION_MOVE_ON,
                "disposition_note": note,
                "followup_gap": False,
                "worked_lead": profile.get("worked_lead") or outbound_count > 0,
            }
        )

    return profile


def build_message_profile(
    messages: list[dict[str, Any]],
    conv: dict[str, Any],
    contact: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Aggregate timestamps, transcript text, intent, and follow-up adequacy for one thread."""
    now = datetime.now(timezone.utc)
    last_inbound: datetime | None = None
    last_outbound: datetime | None = None
    last_touch: datetime | None = None
    inbound_after_outbound_gap: timedelta | None = None
    excerpts: list[str] = []
    has_call = False
    outbound_count = 0
    inbound_count = 0
    inbound_bodies: list[str] = []
    outbound_bodies: list[str] = []

    for m in messages:
        direction = message_direction(m)
        mtype = (m.get("type") or "").lower()
        body = (m.get("body") or m.get("message") or "").strip()
        ts = parse_ts(m.get("dateAdded") or m.get("dateUpdated"))
        if not ts:
            continue
        last_touch = ts if not last_touch or ts > last_touch else last_touch
        if body:
            excerpts.append(f"[{direction or mtype} {ts.isoformat()}] {body[:800]}")
        if direction == "inbound" and body:
            inbound_bodies.append(body)
        elif direction == "outbound" and body:
            outbound_bodies.append(body)
        if "call" in mtype or "voicemail" in mtype or "voice" in mtype or "transcript" in mtype:
            has_call = True
        if direction == "inbound":
            inbound_count += 1
            last_inbound = ts
            if last_outbound and ts > last_outbound:
                inbound_after_outbound_gap = ts - last_outbound
        elif direction == "outbound":
            outbound_count += 1
            last_outbound = ts

    if not messages:
        body = str(conv.get("lastMessageBody") or "").strip()
        if not body:
            return None
        last_touch = parse_ts(conv.get("lastMessageDate"))
        excerpts = [body[:1500]]
        has_call = "call" in body.lower() or "voicemail" in body.lower() or "transcript" in body.lower()
        mtype = str(conv.get("lastMessageType") or "").lower()
        direction = str(
            conv.get("lastMessageDirection") or conv.get("direction") or ""
        ).lower()
        if (
            "outbound" in mtype
            or "outgoing" in direction
            or "outbound" in direction
            or is_our_outbound_script(body)
        ):
            last_outbound = last_touch
            outbound_count = 1
            outbound_bodies = [body]
        else:
            last_inbound = last_touch
            inbound_count = 1
            inbound_bodies = [body]

    transcript = "\n".join(excerpts)
    intent_info = classify_lead_intent(transcript)

    adequate_followup = False
    worked_lead = False
    followup_gap_reason: str | None = None
    if last_inbound:
        if last_outbound and last_outbound >= last_inbound:
            worked_lead = True
            reply_gap = last_outbound - last_inbound
            if reply_gap <= FOLLOWUP_REPLY_SLA:
                adequate_followup = True
            # Outbound after inbound = worked; not a missed-opportunity gap even if slow
        elif last_outbound and (now - last_outbound) <= RECENT_OUTBOUND_WINDOW:
            worked_lead = True
            adequate_followup = True
        if not worked_lead:
            age = now - last_inbound
            if age <= timedelta(days=60):
                followup_gap_reason = f"Inbound not replied ({int(age.total_seconds() // 3600)}h ago)"
    elif last_outbound and (now - last_outbound) <= RECENT_OUTBOUND_WINDOW:
        worked_lead = True
        adequate_followup = True

    if (
        worked_lead
        and last_inbound
        and last_outbound
        and last_outbound >= last_inbound
        and (last_outbound - last_inbound) > FOLLOWUP_REPLY_SLA
        and intent_info["intent"] in (INTENT_BONAFIDE_SELLER, INTENT_BONAFIDE_REFERRAL)
    ):
        followup_gap_reason = (
            f"Slow reply ({int((last_outbound - last_inbound).total_seconds() // 3600)}h) "
            "but outbound sent — monitor, not re-engage"
        )

    if has_call and last_inbound and not worked_lead:
        followup_gap_reason = followup_gap_reason or "Inbound call/voicemail without outbound follow-up"

    profile = {
        "conversation_id": conv.get("id"),
        "contact_id": conv.get("contactId"),
        "contact_name": conv.get("contactName"),
        "channel": conv.get("type") or conv.get("lastMessageType"),
        "last_inbound_at": last_inbound,
        "last_outbound_at": last_outbound,
        "last_touch_at": last_touch,
        "transcript_excerpt": transcript[-6000:],
        "inbound_bodies": inbound_bodies,
        "outbound_bodies": outbound_bodies,
        "has_call": has_call,
        "outbound_count": outbound_count,
        "inbound_count": inbound_count,
        "adequate_followup": adequate_followup,
        "worked_lead": worked_lead,
        "followup_gap": bool(followup_gap_reason) and not worked_lead,
        "followup_gap_reason": followup_gap_reason,
        "intent": intent_info["intent"],
        "viability": intent_info["viability"],
        "intent_confidence": intent_info["confidence"],
        "intent_summary": intent_info["summary"],
        "intent_signals": intent_info["signals"],
    }
    return enrich_profile_disposition(profile, contact)


def merge_contact_profiles(
    a: dict[str, Any],
    b: dict[str, Any],
    contact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge two message profiles for the same contact (multiple threads)."""
    merged = dict(a)
    for key in ("last_inbound_at", "last_outbound_at", "last_touch_at"):
        vals = [a.get(key), b.get(key)]
        vals = [v for v in vals if v]
        merged[key] = max(vals) if vals else None
    merged["transcript_excerpt"] = "\n---\n".join(
        filter(None, [a.get("transcript_excerpt"), b.get("transcript_excerpt")])
    )[-8000:]
    merged["inbound_bodies"] = (a.get("inbound_bodies") or []) + (b.get("inbound_bodies") or [])
    merged["outbound_bodies"] = (a.get("outbound_bodies") or []) + (b.get("outbound_bodies") or [])
    merged["outbound_count"] = (a.get("outbound_count") or 0) + (b.get("outbound_count") or 0)
    merged["inbound_count"] = (a.get("inbound_count") or 0) + (b.get("inbound_count") or 0)
    merged["has_call"] = a.get("has_call") or b.get("has_call")
    merged["adequate_followup"] = a.get("adequate_followup") or b.get("adequate_followup")
    merged["worked_lead"] = a.get("worked_lead") or b.get("worked_lead")
    merged["followup_gap"] = a.get("followup_gap") or b.get("followup_gap")
    if b.get("followup_gap_reason"):
        merged["followup_gap_reason"] = "; ".join(
            filter(None, [a.get("followup_gap_reason"), b.get("followup_gap_reason")])
        )
    intent_info = classify_lead_intent(merged.get("transcript_excerpt") or "")
    merged.update(
        {
            "intent": intent_info["intent"],
            "viability": intent_info["viability"],
            "intent_confidence": intent_info["confidence"],
            "intent_summary": intent_info["summary"],
            "intent_signals": intent_info["signals"],
        }
    )
    return enrich_profile_disposition(merged, contact)


def is_viable_for_seller_reengage(profile: dict[str, Any] | None) -> tuple[bool, str]:
    """Return (include?, exclusion_or_inclusion_reason)."""
    if not profile:
        return False, "No conversation transcript — cannot confirm bonafide seller interest"

    disposition = profile.get("disposition")
    if disposition == DISPOSITION_LANDLINE:
        return False, profile.get("disposition_note") or "Landline — cannot receive SMS"
    if disposition == DISPOSITION_OUTBOUND_ONLY:
        return False, profile.get("disposition_note") or "Outbound-only — not a missed inbound follow-up"
    if disposition == DISPOSITION_MOVE_ON:
        return False, profile.get("disposition_note") or "Non-viable — move on"
    if profile.get("landline"):
        return False, profile.get("disposition_note") or "Landline detected — SMS not viable"

    intent = profile.get("intent")
    if intent in (INTENT_NON_VIABLE, INTENT_REFERRAL_LOW):
        return False, profile.get("intent_summary") or "Non-viable lead"

    if intent == INTENT_BONAFIDE_REFERRAL:
        return True, "Bonafide referral — follow up for property-owner intro, not seller appointment"

    if intent == INTENT_BONAFIDE_SELLER:
        return True, "Bonafide direct seller interest"

    if intent == INTENT_UNCLEAR:
        if profile.get("followup_gap") and not profile.get("worked_lead"):
            return True, "Unclear intent but unanswered inbound — qualify on callback"
        return False, "Intent unclear and no confirmed follow-up gap"

    return False, "Does not meet re-engage viability criteria"


def assess_conversation_gap(profile: dict[str, Any], conv: dict[str, Any]) -> dict[str, Any] | None:
    """Flag conversation only when viable interest AND a real follow-up gap."""
    viable, viability_note = is_viable_for_seller_reengage(profile)
    unread = conv.get("unreadCount") or 0

    missed_reason: str | None = None
    if profile.get("followup_gap") and not profile.get("worked_lead"):
        if viable:
            missed_reason = profile.get("followup_gap_reason")
        else:
            missed_reason = None  # gap exists but lead not viable — not a missed seller opp
    elif unread and viable and not profile.get("worked_lead"):
        missed_reason = f"Unread thread ({unread} unread)"

    if not missed_reason:
        return None

    review = {
        "conversation_id": profile.get("conversation_id"),
        "contact_id": profile.get("contact_id"),
        "contact_name": profile.get("contact_name"),
        "channel": profile.get("channel"),
        "last_inbound_at": profile.get("last_inbound_at"),
        "last_outbound_at": profile.get("last_outbound_at"),
        "missed_opportunity": missed_reason,
        "transcript_excerpt": profile.get("transcript_excerpt"),
        "call_no_followup": profile.get("has_call")
        and profile.get("last_inbound_at")
        and (
            not profile.get("last_outbound_at")
            or profile.get("last_outbound_at") < profile.get("last_inbound_at")
        ),
        "intent": profile.get("intent"),
        "viability": profile.get("viability"),
        "intent_summary": viability_note,
        "adequate_followup": profile.get("adequate_followup"),
        "inbound_bodies": profile.get("inbound_bodies") or [],
        "outbound_bodies": profile.get("outbound_bodies") or [],
        "disposition": profile.get("disposition"),
        "disposition_note": profile.get("disposition_note"),
        "landline": profile.get("landline"),
        "ghl_tags_recommended": profile.get("ghl_tags_recommended"),
    }
    review.update(diagnose_process_failure(profile, review))
    return review


def analyze_conversation(
    messages: list[dict[str, Any]],
    conv: dict[str, Any],
    contact: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    profile = build_message_profile(messages, conv, contact)
    if not profile:
        return None
    return assess_conversation_gap(profile, conv)


def analyze_conversation_batch(
    conversations: list[dict[str, Any]],
    pit: str,
    loc: str,
    available: set[str],
    contacts_by_id: dict[str, dict[str, Any]],
    contact_profiles: dict[str, dict[str, Any]],
    conv_reviews: list[dict[str, Any]],
    llm_threads: list[dict[str, Any]],
    seen_conv_ids: set[str],
    *,
    label: str = "",
) -> None:
    total = len(conversations)
    for i, conv in enumerate(conversations):
        cid_conv = conv.get("id")
        if not cid_conv or cid_conv in seen_conv_ids:
            continue
        seen_conv_ids.add(cid_conv)
        contact = contacts_by_id.get(conv.get("contactId") or "")
        msgs = fetch_messages(pit, loc, available, cid_conv)
        profile = build_message_profile(msgs, conv, contact)
        if profile:
            contact_id = profile.get("contact_id")
            if contact_id:
                if contact_id in contact_profiles:
                    contact_profiles[contact_id] = merge_contact_profiles(
                        contact_profiles[contact_id], profile, contacts_by_id.get(contact_id)
                    )
                else:
                    contact_profiles[contact_id] = profile
            review = assess_conversation_gap(profile, conv)
        else:
            review = None
            if (conv.get("unreadCount") or 0) > 0:
                fallback = build_message_profile([], conv, contact)
                if fallback:
                    review = assess_conversation_gap(fallback, conv)
        if review:
            conv_reviews.append(review)
            llm_threads.append(
                {
                    "contact": review.get("contact_name"),
                    "intent": review.get("intent"),
                    "viability": review.get("viability"),
                    "issue": review.get("missed_opportunity"),
                    "what_went_wrong": review.get("what_went_wrong"),
                    "process_improvement": review.get("process_improvement"),
                    "contact_specific_hook": review.get("contact_specific_hook"),
                    "transcript": review.get("transcript_excerpt", "")[:2000],
                }
            )
        if (i + 1) % 25 == 0:
            prefix = f"{label} " if label else ""
            print(f"  {prefix}reviewed {i + 1}/{total} threads...")


def build_reengage_leads(
    contacts: list[dict[str, Any]],
    opps: list[dict[str, Any]],
    conv_reviews: list[dict[str, Any]],
    contact_profiles: dict[str, dict[str, Any]],
    stage_map: dict[str, str],
    pipelines: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    now = datetime.now(timezone.utc)
    leads: dict[str, dict[str, Any]] = {}
    excluded: list[dict[str, Any]] = []
    conv_by_contact = {c.get("contact_id"): c for c in conv_reviews if c.get("contact_id")}

    pipe_names = {p["id"]: p.get("name") for p in pipelines if p.get("id")}

    def record_excluded(
        contact: dict[str, Any],
        profile: dict[str, Any] | None,
        reason: str,
        *,
        would_have_flagged: str | None = None,
    ) -> None:
        excluded.append(
            {
                "contact_id": contact.get("id"),
                "contact_name": contact.get("contactName")
                or f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip(),
                "phone": contact.get("phone"),
                "exclude_reason": reason,
                "prior_flag": would_have_flagged,
                "intent": (profile or {}).get("intent"),
                "intent_summary": (profile or {}).get("intent_summary"),
                "last_outbound_at": (profile or {}).get("last_outbound_at"),
                "disposition": (profile or {}).get("disposition"),
                "disposition_note": (profile or {}).get("disposition_note"),
                "ghl_tags_recommended": (profile or {}).get("ghl_tags_recommended"),
            }
        )

    for c in contacts:
        cid = c.get("id")
        if not cid:
            continue
        profile = contact_profiles.get(cid)
        date_added = parse_ts(c.get("dateAdded"))
        contact_last = parse_ts(c.get("lastActivity") or c.get("dateAdded"))
        msg_last = (profile or {}).get("last_touch_at")
        last_act = max(filter(None, [contact_last, msg_last]), default=contact_last)
        age_days = (now - date_added).days if date_added else 999
        stale_days = (now - last_act).days if last_act else 999

        viable, viability_note = is_viable_for_seller_reengage(profile)
        worked = profile.get("worked_lead") if profile else False

        if profile and (
            profile.get("landline")
            or profile.get("disposition")
            in (DISPOSITION_LANDLINE, DISPOSITION_OUTBOUND_ONLY, DISPOSITION_MOVE_ON)
        ):
            record_excluded(
                c,
                profile,
                profile.get("disposition_note") or viability_note,
                would_have_flagged=conv_by_contact.get(cid, {}).get("missed_opportunity"),
            )
            continue

        legacy_reasons: list[str] = []
        if date_added and age_days <= 30 and stale_days >= 7:
            legacy_reasons.append(f"Recent lead ({age_days}d old) but no activity for {stale_days}d")
        tags = c.get("tags") or []
        tag_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
        if any(t in tag_str.lower() for t in ("seller", "motivated", "lead", "hot")) and stale_days >= 3:
            legacy_reasons.append("Seller-tagged contact going cold")

        if cid in conv_by_contact:
            cr = conv_by_contact[cid]
            if not viable:
                record_excluded(
                    c,
                    profile,
                    viability_note,
                    would_have_flagged=cr.get("missed_opportunity"),
                )
                continue
            if worked:
                record_excluded(
                    c,
                    profile,
                    f"Follow-up already sent; not a missed opportunity — {viability_note}",
                    would_have_flagged=cr.get("missed_opportunity"),
                )
                continue

        if legacy_reasons and not viable:
            if legacy_reasons:
                record_excluded(
                    c,
                    profile,
                    viability_note or "Stale contact flag suppressed — no bonafide seller/referral intent",
                    would_have_flagged="; ".join(legacy_reasons),
                )
            continue

        if legacy_reasons and worked:
            record_excluded(
                c,
                profile,
                f"Recent outbound SMS/call — lead worked; not a re-engage gap ({viability_note})",
                would_have_flagged="; ".join(legacy_reasons),
            )
            continue

        reasons: list[str] = []
        priority = "medium"
        action = "SMS + call re-engagement; verify motivation and timeline."

        if cid in conv_by_contact:
            cr = conv_by_contact[cid]
            reasons.append(cr.get("missed_opportunity") or "Conversation follow-up gap")
            priority = "critical" if cr.get("call_no_followup") else "high"
            if profile and profile.get("intent") == INTENT_BONAFIDE_REFERRAL:
                action = "Call referrer; secure intro to property owner; explain referral program."
            else:
                action = "Call back today; reference last inbound; qualify motivation and book seller appointment."

        if legacy_reasons and viable and not worked:
            reasons.extend(legacy_reasons)
            if priority == "medium":
                priority = "high"

        if not reasons:
            continue

        intent_label = (profile or {}).get("intent") or INTENT_UNCLEAR
        cr = conv_by_contact.get(cid)
        leads[cid] = {
            "contact_id": cid,
            "contact_name": c.get("contactName") or f"{c.get('firstName', '')} {c.get('lastName', '')}".strip(),
            "phone": c.get("phone"),
            "email": c.get("email"),
            "date_added": date_added,
            "last_activity": last_act,
            "priority": priority,
            "reason": "; ".join(reasons),
            "suggested_action": action,
            "pipeline_name": None,
            "stage_name": None,
            "tags": tag_str,
            "intent": intent_label,
            "viability": (profile or {}).get("viability") or "unclear",
            "intent_summary": viability_note,
            "last_outbound_at": (profile or {}).get("last_outbound_at"),
            "transcript_excerpt": (profile or {}).get("transcript_excerpt"),
            "what_went_wrong": (cr or {}).get("what_went_wrong"),
            "process_improvement": (cr or {}).get("process_improvement"),
            "contact_specific_hook": (cr or {}).get("contact_specific_hook"),
        }

    for o in opps:
        cid = o.get("contactId")
        if not cid or cid in leads:
            continue
        profile = contact_profiles.get(cid)
        viable, viability_note = is_viable_for_seller_reengage(profile)
        if not viable and profile:
            continue
        updated = parse_ts(o.get("updatedAt"))
        if updated and (now - updated).days >= 14 and (o.get("status") or "").lower() not in ("won", "lost"):
            stage = stage_map.get(o.get("pipelineStageId"), "?")
            pipe = pipe_names.get(o.get("pipelineId"), "?")
            leads[cid] = {
                "contact_id": cid,
                "contact_name": o.get("name"),
                "phone": None,
                "email": None,
                "date_added": parse_ts(o.get("createdAt")),
                "last_activity": updated,
                "priority": "medium",
                "reason": f"Open opportunity stale {(now - updated).days}d in {stage}",
                "suggested_action": "Review deal; call to re-qualify; move stage or mark dead.",
                "pipeline_name": pipe,
                "stage_name": stage,
                "tags": "",
                "intent": (profile or {}).get("intent") or INTENT_UNCLEAR,
                "viability": (profile or {}).get("viability") or "unclear",
                "intent_summary": viability_note if profile else "Open opp — verify seller intent on call",
                "last_outbound_at": (profile or {}).get("last_outbound_at"),
                "transcript_excerpt": (profile or {}).get("transcript_excerpt"),
            }

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    result = list(leads.values())
    result.sort(
        key=lambda x: (
            order.get(x.get("priority", "low"), 9),
            -(
                parse_ts(x.get("date_added") or x.get("last_activity") or datetime.min.replace(tzinfo=timezone.utc))
                or datetime.min.replace(tzinfo=timezone.utc)
            ).timestamp(),
        )
    )
    excluded.sort(
        key=lambda x: (x.get("contact_name") or "").lower(),
    )
    return result, excluded


def first_name_from(contact_name: str | None) -> str:
    if not contact_name:
        return "there"
    parts = contact_name.strip().split()
    return parts[0] if parts else "there"


def _shorten_phrase(text: str, max_len: int = 85) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


def extract_last_inbound_snippet(transcript: str, max_len: int = 90) -> str:
    """Pull the most recent inbound line from a transcript excerpt."""
    intel = extract_contact_intel(transcript)
    if intel.get("last_inbound"):
        return _shorten_phrase(intel["last_inbound"], max_len)
    return ""


def extract_property_hint(transcript: str) -> str:
    if not transcript:
        return ""
    for pattern in (
        r"\b(\d+\s+[\w\s]{2,35}(?:st|street|ave|avenue|rd|road|dr|drive|ln|lane|way|blvd)\.?)\b",
        r"\b(?:property|house|home) (?:on|at|in|near) ([^.?!\n,]{4,40})",
        r"\bin ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),?\s+(?:FL|Florida|[A-Z]{2})\b",
    ):
        m = re.search(pattern, transcript, re.I)
        if m:
            return m.group(1).strip()[:50]
    return ""


SITUATION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("divorce", re.compile(r"\bdivorc", re.I)),
    ("probate/inheritance", re.compile(r"\bprobate\b|\binherited\b|\bestate\b|\bpassed away\b", re.I)),
    ("repairs needed", re.compile(r"\brepairs?\b|\bfixer\b|\bneeds work\b|\bas-?is\b|\bfoundation\b|\broof\b", re.I)),
    ("tenant-occupied", re.compile(r"\btenant\b|\brental\b|\blease\b|\boccupied\b", re.I)),
    ("behind on payments", re.compile(r"\bbehind on\b|\bforeclosure\b|\bpre-foreclosure\b|\blate on mortgage\b", re.I)),
    ("relocating", re.compile(r"\bmoving\b|\brelocat\b|\bjob transfer\b|\bout of state\b", re.I)),
    ("timeline pressure", re.compile(r"\bneed to (?:sell|close)\b|\bby (?:end of|next)\b|\bwithin \d+ (?:days|weeks|months)\b", re.I)),
]


def extract_contact_intel(
    transcript: str,
    inbound_bodies: list[str] | None = None,
    outbound_bodies: list[str] | None = None,
) -> dict[str, Any]:
    """Extract specific hooks from transcript for personalized SMS and coaching."""
    inbounds = list(inbound_bodies or [])
    outbounds = list(outbound_bodies or [])
    if transcript and not inbounds:
        for line in transcript.split("\n"):
            lower = line.lower()
            body = line.split("]", 1)[1].strip() if "]" in line else line.strip()
            if not body:
                continue
            if "[inbound" in lower or "incoming" in lower:
                inbounds.append(body)
            elif "[outbound" in lower or "outgoing" in lower:
                outbounds.append(body)

    all_inbound = " ".join(inbounds)
    situations: list[str] = []
    for label, pattern in SITUATION_PATTERNS:
        if pattern.search(all_inbound):
            situations.append(label)

    questions: list[str] = []
    for body in inbounds:
        for match in re.finditer(r"[^.?!]{8,}[?]", body):
            q = match.group(0).strip()
            if is_our_outbound_script(q):
                continue
            if q not in questions:
                questions.append(q)

    timeline = ""
    tm = re.search(
        r"(?:need|want|have) to (?:sell|close)[^.?!]{0,25}(?:by|before|within|in \d+)[^.?!]{0,45}",
        all_inbound,
        re.I,
    )
    if tm:
        timeline = tm.group(0).strip()

    property_hint = extract_property_hint(all_inbound or transcript)
    last_inbound = inbounds[-1] if inbounds else ""

    specific_hook = ""
    if questions:
        specific_hook = questions[-1]
    elif situations and property_hint:
        specific_hook = f"{situations[0]} at {property_hint}"
    elif situations and timeline:
        specific_hook = f"{situations[0]} — {timeline}"
    elif situations:
        specific_hook = situations[0]
    elif timeline:
        specific_hook = timeline
    elif property_hint:
        specific_hook = property_hint
    elif last_inbound and len(last_inbound) > 20:
        specific_hook = last_inbound

    has_actionable_intel = bool(
        property_hint
        or situations
        or questions
        or timeline
        or (last_inbound and len(last_inbound) > 35)
    )

    return {
        "inbound_messages": inbounds,
        "outbound_messages": outbounds,
        "property_hint": property_hint,
        "situations": situations,
        "timeline": timeline,
        "questions": questions,
        "last_inbound": last_inbound,
        "specific_hook": _shorten_phrase(specific_hook, 120) if specific_hook else "",
        "has_actionable_intel": has_actionable_intel,
    }


def diagnose_process_failure(profile: dict[str, Any], review: dict[str, Any]) -> dict[str, str]:
    """Identify what went wrong in the thread and how to improve next time."""
    if profile.get("landline") or profile.get("disposition") == DISPOSITION_LANDLINE:
        return {
            "what_went_wrong": profile.get("disposition_note")
            or "Landline detected — SMS cannot deliver to this number",
            "process_improvement": (
                "Tag contact `landline` + `no-sms` in GHL; remove from SMS workflows; "
                "call-only or archive. Do not count as missed SMS follow-up."
            ),
            "contact_specific_hook": "",
        }
    if profile.get("disposition") == DISPOSITION_OUTBOUND_ONLY:
        last_out = (profile.get("outbound_bodies") or [""])[-1][:80]
        return {
            "what_went_wrong": (
                profile.get("disposition_note")
                or f"Only our outbound was sent (e.g. {last_out!r}) — no inbound reply"
            ),
            "process_improvement": (
                "Verify number type before SMS drip; auto-tag landline on delivery failure; "
                "move to call queue or archive — not a re-engage gap."
            ),
            "contact_specific_hook": "",
        }
    if profile.get("disposition") == DISPOSITION_MOVE_ON:
        return {
            "what_went_wrong": profile.get("disposition_note") or "Non-viable lead — move on",
            "process_improvement": "Do not re-engage; document disposition in GHL and close thread.",
            "contact_specific_hook": "",
        }

    intel = extract_contact_intel(
        profile.get("transcript_excerpt") or "",
        profile.get("inbound_bodies"),
        profile.get("outbound_bodies"),
    )
    failures: list[str] = []
    improvements: list[str] = []
    missed = review.get("missed_opportunity") or ""

    if profile.get("followup_gap") and not profile.get("worked_lead"):
        failures.append("Seller inbound never received an outbound reply")
        improvements.append(
            "Automation: trigger on inbound SMS/call - SMS within 5 min + task assigned to acq rep"
        )

    if review.get("call_no_followup"):
        failures.append("Inbound call/voicemail with no callback or follow-up text")
        improvements.append(
            "Enable missed-call text-back workflow (<2 min): 'Sorry we missed you — when's a good time?'"
        )

    last_in = profile.get("last_inbound_at")
    last_out = profile.get("last_outbound_at")
    if last_in and last_out and last_out >= last_in:
        gap_h = int((last_out - last_in).total_seconds() // 3600)
        if gap_h > FOLLOWUP_REPLY_SLA.total_seconds() // 3600:
            failures.append(f"Reply took {gap_h}h — exceeded {int(FOLLOWUP_REPLY_SLA.total_seconds() // 3600)}h speed-to-lead target")
            improvements.append(
                "Alert on leads unanswered >15 min; REI benchmark is first human/automated touch in <5 min"
            )

    if intel["questions"] and not profile.get("worked_lead"):
        real_questions = [q for q in intel["questions"] if not is_our_outbound_script(q)]
        if real_questions:
            q = _shorten_phrase(real_questions[-1], 70)
            failures.append(f"Contact asked a direct question that was never answered: \"{q}\"")
            improvements.append(
                "Script fix: answer their exact question first, then offer next step (call/appointment)"
            )

    intent = profile.get("intent")
    outbound_text = " ".join(intel["outbound_messages"]).lower()
    if intent == INTENT_BONAFIDE_SELLER and intel["outbound_messages"]:
        if not re.search(r"\b(?:appointment|visit|meet|come (?:by|out)|look at|stop by|walkthrough)\b", outbound_text):
            failures.append("Rep engaged seller but never attempted to set an appointment/walkthrough")
            improvements.append(
                "After qualifying motivation, always ask for a specific day/time: 'Can I see it Thursday or Friday?'"
            )
        if intel["situations"] and not any(s.lower()[:6] in outbound_text for s in intel["situations"]):
            failures.append(
                f"Contact shared situation ({intel['situations'][0]}) but outbound did not acknowledge it"
            )
            improvements.append(
                "Mirror their situation in replies — shows listening and builds trust before the ask"
            )

    if intent == INTENT_BONAFIDE_REFERRAL and not profile.get("worked_lead"):
        failures.append("Referrer showed interest but we did not ask for an intro to the property owner")
        improvements.append(
            "Referrer script: thank them, explain referral fee/process, ask for owner name + best intro method"
        )

    if not failures and missed:
        failures.append(missed)

    if not improvements:
        improvements.append("Review thread in GHL; document playbook update for this scenario")

    return {
        "what_went_wrong": "; ".join(failures),
        "process_improvement": "; ".join(improvements),
        "contact_specific_hook": intel.get("specific_hook") or "",
    }


def build_sms_context(
    lead: dict[str, Any],
    contact: dict[str, Any] | None,
    profile: dict[str, Any] | None,
    conv_review: dict[str, Any] | None,
    location_name: str,
) -> dict[str, Any]:
    transcript = (
        (profile or {}).get("transcript_excerpt")
        or (conv_review or {}).get("transcript_excerpt")
        or ""
    )
    contact = contact or {}
    name = lead.get("contact_name") or contact.get("contactName") or ""
    intel = extract_contact_intel(
        transcript,
        (profile or {}).get("inbound_bodies") or (conv_review or {}).get("inbound_bodies"),
        (profile or {}).get("outbound_bodies") or (conv_review or {}).get("outbound_bodies"),
    )
    return {
        "contact_id": lead.get("contact_id"),
        "first_name": first_name_from(name),
        "full_name": name,
        "intent": lead.get("intent"),
        "reason": lead.get("reason"),
        "tags": lead.get("tags") or "",
        "location_name": location_name,
        "transcript": transcript[:2500],
        "intel": intel,
        "last_inbound_snippet": _shorten_phrase(intel.get("last_inbound") or "", 90),
        "property_hint": intel.get("property_hint") or "",
        "specific_hook": (conv_review or {}).get("contact_specific_hook") or intel.get("specific_hook") or "",
        "has_actionable_intel": intel.get("has_actionable_intel", False),
        "missed_opportunity": (conv_review or {}).get("missed_opportunity") or lead.get("reason"),
        "what_went_wrong": (conv_review or {}).get("what_went_wrong") or "",
        "call_no_followup": (conv_review or {}).get("call_no_followup", False),
        "pipeline": lead.get("pipeline_name"),
        "stage": lead.get("stage_name"),
    }


def compose_followup_sms_rule(ctx: dict[str, Any]) -> str:
    """Rule-based SMS — specific to contact intel; generic only when nothing else available."""
    name = ctx["first_name"]
    intel = ctx.get("intel") or {}
    hook = ctx.get("specific_hook") or intel.get("specific_hook") or ""
    prop = intel.get("property_hint") or ctx.get("property_hint") or ""
    intent = ctx.get("intent")
    call = ctx.get("call_no_followup")
    has_intel = ctx.get("has_actionable_intel", False)
    questions = intel.get("questions") or []
    situations = intel.get("situations") or []
    timeline = intel.get("timeline") or ""

    if has_intel:
        if intent == INTENT_BONAFIDE_REFERRAL:
            if hook:
                ref = _shorten_phrase(hook, 70)
                return (
                    f"Hi {name}, thanks again — you mentioned {ref}. "
                    "If the owner wants a no-pressure cash offer, I can reach out directly. "
                    "Would you be open to a quick intro this week?"
                )
            if prop:
                return (
                    f"Hi {name}, following up on the property at {prop} you mentioned. "
                    "Happy to connect with the owner directly if they're open to an offer. "
                    "Reply YES and I'll send our referral next steps."
                )

        if questions:
            q = _shorten_phrase(questions[-1], 75)
            return (
                f"Hi {name}, sorry for the delay — you asked \"{q}\" "
                "Happy to answer that and see if we're a fit. Still interested in chatting?"
            )

        if situations and prop:
            return (
                f"Hi {name}, circling back on {prop} and your {situations[0]} situation. "
                "We buy as-is for cash with a flexible close. "
                "Are you still looking for options? I can call today if easier."
            )

        if timeline and prop:
            return (
                f"Hi {name}, wanted to follow up on {prop} — you mentioned {timeline.lower()}. "
                "We may still be able to help with a fast cash close. Worth a quick call?"
            )

        if hook:
            ref = _shorten_phrase(hook, 80)
            return (
                f"Hi {name}, following up on what you shared: {ref}. "
                "We buy locally for cash, as-is. Are you still exploring options?"
            )

        if prop:
            return (
                f"Hi {name}, checking back on {prop}. "
                "We're still buying in the area for cash — want a no-obligation ballpark offer?"
            )

        if call:
            return (
                f"Hi {name}, sorry I missed you after your call"
                + (f" about {prop}" if prop else "")
                + ". Still happy to talk through options — reply with a good time to call."
            )

    # Generic fallback — only when intel is name/address-level at best
    if prop:
        return (
            f"Hi {name}, checking back on {prop}. "
            "We buy for cash as-is — reply YES if you'd like a ballpark offer."
        )
    return (
        f"Hi {name}, wanted to reconnect about selling your property. "
        "We buy homes as-is for cash — reply YES if you'd like to chat."
    )


def _trim_sms(text: str, max_len: int = 320) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


def _sms_references_intel(sms: str, ctx: dict[str, Any]) -> bool:
    """Heuristic: LLM SMS must echo something from the contact's thread."""
    if not sms:
        return False
    intel = ctx.get("intel") or {}
    sms_lower = sms.lower()
    for token in (
        intel.get("property_hint"),
        intel.get("specific_hook"),
        intel.get("timeline"),
        *(intel.get("situations") or []),
    ):
        if token and len(str(token)) > 4:
            words = [w for w in re.findall(r"[a-z0-9]+", str(token).lower()) if len(w) > 4]
            if words and any(w in sms_lower for w in words[:3]):
                return True
    if intel.get("questions"):
        qwords = re.findall(r"[a-z]{5,}", intel["questions"][-1].lower())
        if qwords and sum(1 for w in qwords[:4] if w in sms_lower) >= 2:
            return True
    return not ctx.get("has_actionable_intel")


def llm_enrich_gap_leads_batch(
    contexts: list[dict[str, Any]], api_key: str, location_name: str, vertical: str = VERTICAL_GENERIC
) -> dict[str, dict[str, str]]:
    """Generate specific SMS + process coaching per viable gap lead."""
    if not contexts:
        return {}
    payload = []
    for c in contexts[:40]:
        intel = c.get("intel") or {}
        payload.append(
            {
                "contact_id": c["contact_id"],
                "name": c["full_name"],
                "intent": c["intent"],
                "missed_opportunity": c.get("missed_opportunity"),
                "what_went_wrong": c.get("what_went_wrong"),
                "specific_hook": c.get("specific_hook"),
                "property": intel.get("property_hint"),
                "situations": intel.get("situations"),
                "timeline": intel.get("timeline"),
                "questions": intel.get("questions"),
                "last_inbound": intel.get("last_inbound", "")[:500],
                "transcript": c.get("transcript", "")[:1500],
                "has_actionable_intel": c.get("has_actionable_intel"),
            }
        )
    if vertical == VERTICAL_REI:
        coach = f"You are a REI acquisitions coach for {location_name} (cash home buyer).\n"
        system = "REI coach + SMS writer. Every SMS must prove you read their message. JSON only."
    else:
        coach = (
            f"You are a CRM follow-up coach for {location_name}.\n"
            "Focus on helpful, specific re-engagement — not industry-specific assumptions.\n"
        )
        system = "CRM coach + SMS writer. Every SMS must reference the contact's message. JSON only."
    prompt = (
        coach
        + "For EACH contact, return:\n"
        "1. suggested_sms — ONE follow-up SMS under 300 chars that MUST reference something "
        "specific the CONTACT said (their question, situation, property detail, timeline, address). "
        "Quote or paraphrase their words. Generic 'still interested in selling?' is ONLY allowed "
        "when has_actionable_intel is false.\n"
        "2. process_improvement — what went wrong in OUR handling and a concrete future fix "
        "(automation, script, training). Be specific to this thread.\n"
        "3. contact_specific_hook — the exact phrase/detail the SMS references (for audit trail).\n\n"
        "Return ONLY JSON: {\"leads\": [{\"contact_id\", \"suggested_sms\", \"process_improvement\", "
        "\"contact_specific_hook\"}, ...]}\n\n"
        + json.dumps(payload, default=str)
    )
    body = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": system,
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 4000,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            items = parsed.get("leads") or parsed.get("messages") or []
            out: dict[str, dict[str, str]] = {}
            for item in items:
                cid = str(item.get("contact_id") or "")
                if not cid:
                    continue
                out[cid] = {
                    "suggested_sms": _trim_sms(item.get("suggested_sms") or item.get("sms") or ""),
                    "process_improvement": (item.get("process_improvement") or "").strip(),
                    "contact_specific_hook": (item.get("contact_specific_hook") or "").strip(),
                }
            return out
    except (urllib.error.HTTPError, KeyError, TimeoutError, json.JSONDecodeError, ValueError) as e:
        print(f"  LLM enrichment skipped: {e}")
        return {}


def enrich_with_followup_sms(
    leads: list[dict[str, Any]],
    conv_reviews: list[dict[str, Any]],
    contacts_by_id: dict[str, dict[str, Any]],
    contact_profiles: dict[str, dict[str, Any]],
    location_name: str,
    api_key: str | None = None,
    vertical: str = VERTICAL_GENERIC,
) -> None:
    """Add suggested_sms, process_improvement, and contact_specific_hook (in-place)."""
    conv_by_contact = {r.get("contact_id"): r for r in conv_reviews if r.get("contact_id")}
    contexts: list[dict[str, Any]] = []

    for lead in leads:
        cid = lead.get("contact_id")
        profile = contact_profiles.get(cid or "")
        conv = conv_by_contact.get(cid)
        ctx = build_sms_context(lead, contacts_by_id.get(cid or ""), profile, conv, location_name)
        lead["_sms_ctx"] = ctx
        if conv:
            lead.setdefault("what_went_wrong", conv.get("what_went_wrong"))
            lead.setdefault("process_improvement", conv.get("process_improvement"))
            lead.setdefault("contact_specific_hook", conv.get("contact_specific_hook"))
        contexts.append(ctx)

    llm_enrich: dict[str, dict[str, str]] = {}
    if api_key and contexts:
        print(f"Generating specific SMS + coaching for {len(contexts)} leads...")
        llm_enrich = llm_enrich_gap_leads_batch(contexts, api_key, location_name, vertical)

    for lead in leads:
        ctx = lead.pop("_sms_ctx", {})
        cid = str(lead.get("contact_id") or "")
        enriched = llm_enrich.get(cid) or {}
        rule_sms = compose_followup_sms_rule(ctx)
        sms = enriched.get("suggested_sms") or rule_sms
        if enriched.get("suggested_sms") and not _sms_references_intel(sms, ctx):
            sms = rule_sms
        lead["suggested_sms"] = _trim_sms(sms)
        lead["contact_specific_hook"] = (
            enriched.get("contact_specific_hook")
            or ctx.get("specific_hook")
            or lead.get("contact_specific_hook")
            or ""
        )
        if enriched.get("process_improvement"):
            lead["process_improvement"] = enriched["process_improvement"]
        elif not lead.get("process_improvement") and conv_by_contact.get(lead.get("contact_id")):
            lead["process_improvement"] = conv_by_contact[lead["contact_id"]].get("process_improvement", "")

    for review in conv_reviews:
        cid = review.get("contact_id")
        lead_match = next((L for L in leads if L.get("contact_id") == cid), None)
        if lead_match:
            for key in ("suggested_sms", "process_improvement", "contact_specific_hook", "what_went_wrong"):
                if lead_match.get(key):
                    review[key] = lead_match[key]
            continue
        profile = contact_profiles.get(cid or "")
        stub_lead = {
            "contact_id": cid,
            "contact_name": review.get("contact_name"),
            "intent": review.get("intent"),
            "reason": review.get("missed_opportunity"),
        }
        ctx = build_sms_context(stub_lead, contacts_by_id.get(cid or ""), profile, review, location_name)
        enriched = llm_enrich.get(str(cid)) or {}
        sms = enriched.get("suggested_sms") or compose_followup_sms_rule(ctx)
        if enriched.get("suggested_sms") and not _sms_references_intel(sms, ctx):
            sms = compose_followup_sms_rule(ctx)
        review["suggested_sms"] = _trim_sms(sms)
        review["contact_specific_hook"] = enriched.get("contact_specific_hook") or ctx.get("specific_hook") or ""
        if enriched.get("process_improvement"):
            review["process_improvement"] = enriched["process_improvement"]


def llm_conversation_summary(threads: list[dict[str, Any]], api_key: str, vertical: str = VERTICAL_GENERIC) -> str:
    if not threads:
        return ""
    payload_threads = threads[:12]
    if vertical == VERTICAL_REI:
        prompt = (
            "You are a master REI acquisitions director reviewing GHL SMS/call transcripts. "
            "For each thread identify: (1) what WE did wrong (slow reply, no callback, ignored their question, "
            "never asked for appointment), (2) a concrete process/automation/script fix for the team. "
            "Distinguish non-viable leads from bonafide missed opportunities. Be specific — cite their words.\n\n"
            + json.dumps(payload_threads, default=str)[:12000]
        )
        system = "REI GHL conversion expert. Bullet specific fixes."
    else:
        prompt = (
            "You are a CRM operations lead reviewing GHL SMS/call transcripts. "
            "For each thread identify: (1) what we did wrong (slow reply, no callback, ignored question), "
            "(2) a concrete process/automation fix. Distinguish low-intent from viable missed opportunities. "
            "Be specific — cite their words.\n\n"
            + json.dumps(payload_threads, default=str)[:12000]
        )
        system = "CRM GHL expert. Bullet specific fixes."
    body = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1500,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
    except (urllib.error.HTTPError, KeyError, TimeoutError) as e:
        return f"(LLM analysis skipped: {e})"


def insert_audit_run(account: dict[str, Any], password: str, location_id: str, summary: str) -> int:
    schema = account["schema_prefix"]
    run_id_s = psql_as_account(
        account,
        password,
        f"""
INSERT INTO {schema}.audit_runs (slug, location_id, status, summary, finished_at)
VALUES ({sql_quote(account['slug'])}, {sql_quote(location_id)}, 'completed', {sql_quote(summary)}, now())
RETURNING id;
""",
    )
    return int(run_id_s.strip().splitlines()[0])


def persist_leads(account: dict[str, Any], password: str, run_id: int, leads: list[dict[str, Any]]) -> None:
    schema = account["schema_prefix"]
    for L in leads:
        psql_as_account(
            account,
            password,
            f"""
INSERT INTO {schema}.reengage_leads (
  audit_run_id, contact_id, contact_name, phone, email, date_added, last_activity,
  priority, reason, suggested_action, suggested_sms, contact_specific_hook,
  what_went_wrong, process_improvement, pipeline_name, stage_name, tags
) VALUES (
  {run_id}, {sql_quote(L.get('contact_id'))}, {sql_quote(L.get('contact_name'))},
  {sql_quote(L.get('phone'))}, {sql_quote(L.get('email'))},
  {sql_quote(L.get('date_added').isoformat() if L.get('date_added') else None)},
  {sql_quote(L.get('last_activity').isoformat() if L.get('last_activity') else None)},
  {sql_quote(L.get('priority'))}, {sql_quote(L.get('reason'))},
  {sql_quote(L.get('suggested_action'))}, {sql_quote(L.get('suggested_sms'))},
  {sql_quote(L.get('contact_specific_hook'))}, {sql_quote(L.get('what_went_wrong'))},
  {sql_quote(L.get('process_improvement'))},
  {sql_quote(L.get('pipeline_name'))},
  {sql_quote(L.get('stage_name'))}, {sql_quote(L.get('tags'))}
);
""",
        )


def persist_conv_reviews(account: dict[str, Any], password: str, run_id: int, reviews: list[dict[str, Any]]) -> None:
    schema = account["schema_prefix"]
    for r in reviews:
        psql_as_account(
            account,
            password,
            f"""
INSERT INTO {schema}.conversation_reviews (
  audit_run_id, conversation_id, contact_id, contact_name, channel,
  last_inbound_at, last_outbound_at, missed_opportunity, transcript_excerpt,
  suggested_sms, contact_specific_hook, what_went_wrong, process_improvement
) VALUES (
  {run_id}, {sql_quote(r.get('conversation_id'))}, {sql_quote(r.get('contact_id'))},
  {sql_quote(r.get('contact_name'))}, {sql_quote(r.get('channel'))},
  {sql_quote(r.get('last_inbound_at').isoformat() if r.get('last_inbound_at') else None)},
  {sql_quote(r.get('last_outbound_at').isoformat() if r.get('last_outbound_at') else None)},
  {sql_quote(r.get('missed_opportunity'))}, {sql_quote(r.get('transcript_excerpt'))},
  {sql_quote(r.get('suggested_sms'))}, {sql_quote(r.get('contact_specific_hook'))},
  {sql_quote(r.get('what_went_wrong'))}, {sql_quote(r.get('process_improvement'))}
);
""",
        )


MIN_VIABLE_REENGAGE = 15


def collect_landline_tag_candidates(
    contact_profiles: dict[str, dict[str, Any]],
    contacts_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Contacts that should have landline/no-sms tags in GHL."""
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cid, profile in contact_profiles.items():
        if cid in seen:
            continue
        if not (
            profile.get("landline")
            or profile.get("disposition") in (DISPOSITION_LANDLINE, DISPOSITION_OUTBOUND_ONLY)
        ):
            continue
        contact = contacts_by_id.get(cid) or {}
        existing = contact.get("tags") or []
        tag_str = ", ".join(existing).lower() if isinstance(existing, list) else str(existing).lower()
        if "landline" in tag_str:
            continue
        recommended = profile.get("ghl_tags_recommended") or list(GHL_LANDLINE_TAGS)
        candidates.append(
            {
                "contact_id": cid,
                "contact_name": profile.get("contact_name")
                or contact.get("contactName")
                or f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip(),
                "phone": contact.get("phone"),
                "tags": recommended,
                "reason": profile.get("disposition_note") or "Landline / SMS delivery failure",
            }
        )
        seen.add(cid)
    return candidates


def apply_landline_tags(
    pit: str,
    loc: str,
    available: set[str],
    candidates: list[dict[str, Any]],
) -> tuple[int, list[str]]:
    """Apply landline tags via GHL MCP (Tier B — use with Boss approval)."""
    if "contacts_add-tags" not in available:
        return 0, ["contacts_add-tags tool not available"]
    applied = 0
    errors: list[str] = []
    for item in candidates:
        cid = item.get("contact_id")
        tags = item.get("tags") or GHL_LANDLINE_TAGS
        if not cid:
            continue
        resp = mcp_tool(
            "contacts_add-tags",
            {"contactId": cid, "tags": tags},
            pit,
            loc,
            available,
        )
        if isinstance(resp, dict) and resp.get("_error"):
            errors.append(f"{item.get('contact_name') or cid}: {resp.get('_error')}")
        elif isinstance(resp, dict) and resp.get("_skipped"):
            errors.append(f"{item.get('contact_name') or cid}: tool skipped")
        else:
            applied += 1
    return applied, errors


def write_reports(
    account: dict[str, Any],
    location_name: str,
    field_recs: list[dict[str, str]],
    pipe_recs: list[dict[str, str]],
    auto_recs: list[dict[str, str]],
    fields: list[dict[str, Any]],
    matched_fields: dict[str, list[str]],
    pipelines: list[dict[str, Any]],
    leads: list[dict[str, Any]],
    excluded: list[dict[str, Any]],
    conv_reviews: list[dict[str, Any]],
    llm_summary: str,
    run_id: int,
    vertical: str = VERTICAL_GENERIC,
) -> tuple[Path, Path]:
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    base = OBS / "GHL" / account["obsidian_folder"]
    strat_path = base / "Audits" / f"{today}-strategic-analysis.md"
    reengage_path = base / "Recommendations" / f"{today}-reengage-leads.md"
    csv_path = base / "Recommendations" / f"{today}-reengage-leads.csv"
    strat_path.parent.mkdir(parents=True, exist_ok=True)
    reengage_path.parent.mkdir(parents=True, exist_ok=True)

    all_recs = field_recs + pipe_recs + auto_recs
    lens = (
        "REI — motivated seller → appointment → offer → contract"
        if vertical == VERTICAL_REI
        else "Generic CRM — lead engagement → follow-up → pipeline progression"
    )
    field_label = "REI categories" if vertical == VERTICAL_REI else "CRM categories"
    lines = [
        f"# Strategic GHL analysis — {account['display_name']}",
        "",
        f"- **Location:** {location_name}",
        f"- **Date:** {today}",
        f"- **Audit run:** {run_id}",
        f"- **Lens:** {lens}",
        "",
        "## Executive summary",
        "",
        f"- **Custom fields:** {len(fields)} total; {sum(1 for v in matched_fields.values() if v)} {field_label} matched",
        f"- **Pipelines:** {len(pipelines)}",
        f"- **Re-engage leads:** {len(leads)} viable (engagement + follow-up gap)",
        f"- **Excluded from re-engage:** {len(excluded)} (low intent, referral-only, or already worked)",
        f"- **Conversation gaps:** {len(conv_reviews)} threads flagged (viable + missed follow-up)",
        "",
        "## Review criteria (re-engage vs exclude)",
        "",
        "A contact is added to the re-engage list **only when all apply**:",
        "",
        "1. **Viable interest** — transcript shows real engagement or a serious referral worth pursuing",
        "2. **Real follow-up gap** — inbound unanswered >48h, or no outbound within 7d when nurture was needed",
        "3. **Not already worked** — recent outbound SMS/call counts as follow-up; stale `lastActivity` alone is insufficient",
        "",
        "**Excluded:** low-intent curiosity, tire kickers, DNC, wrong number, "
        "landlines (cannot receive SMS), outbound-only threads with no inbound reply, "
        "or contacts already contacted who were not serious.",
        "",
        "## 1. Pipelines",
        "",
    ]
    for p in pipelines:
        stages = " → ".join(s.get("name", "?") for s in (p.get("stages") or []))
        lines.append(f"- **{p.get('name')}:** {stages or '(no stages)'}")
    lines.extend(["", f"## 2. Custom fields ({field_label})", ""])
    for key, names in matched_fields.items():
        status = "✅ " + ", ".join(names) if names else "❌ missing"
        lines.append(f"- **{key.replace('_', ' ').title()}:** {status}")
    lines.extend(["", "## 3. Automations (inferred + manual verification required)", ""])
    lines.append(
        "GHL MCP cannot list workflows. **Conversation messages** require PIT scope "
        "'View/Edit Conversation Messages' for full SMS/call transcripts; without it, "
        "analysis uses conversation summaries only."
    )
    lines.extend(["", "## 4. Prioritized recommendations", ""])
    for i, r in enumerate(sorted(all_recs, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(x["priority"], 9)), 1):
        lines.append(f"### {i}. [{r['priority'].upper()}] {r['issue']}")
        lines.append(f"\n**Fix:** {r['fix']}\n")

    if llm_summary:
        lines.extend(["## 5. Conversation intelligence (AI review)", "", llm_summary, ""])

    lines.extend(["## 6. Conversation gaps (viable + missed follow-up)", ""])
    for r in conv_reviews[:25]:
        intent = r.get("intent") or "?"
        lines.append(
            f"- **{r.get('contact_name') or r.get('contact_id')}** [{intent}] — {r.get('missed_opportunity')}"
        )
        if r.get("what_went_wrong"):
            lines.append(f"  - *What went wrong:* {r.get('what_went_wrong')}")
        if r.get("process_improvement"):
            lines.append(f"  - *Future fix:* {r.get('process_improvement')}")
        if r.get("contact_specific_hook"):
            lines.append(f"  - *Contact said:* {r.get('contact_specific_hook')}")
        if r.get("suggested_sms"):
            lines.append(f"  - *Suggested SMS:* {r.get('suggested_sms')}")

    if excluded:
        lines.extend(["", "## 7. Excluded from re-engage (reviewed, not viable)", ""])
        for x in excluded[:40]:
            prior = f" (was: {x.get('prior_flag')[:60]})" if x.get("prior_flag") else ""
            disp = x.get("disposition")
            disp_note = f" [{disp}]" if disp else ""
            note = x.get("disposition_note")
            extra = f" — {note[:120]}" if note and note != x.get("exclude_reason") else ""
            lines.append(
                f"- **{x.get('contact_name') or x.get('contact_id')}** ({x.get('phone') or '—'})"
                f"{disp_note} — {x.get('exclude_reason')}{extra}{prior}"
            )
            tags = x.get("ghl_tags_recommended")
            if tags:
                lines.append(f"  - *GHL tags:* {', '.join(tags)}")

    strat_path.write_text("\n".join(lines), encoding="utf-8")

    rg = [
        f"# Re-engage leads — {account['display_name']}",
        "",
        f"Generated {today}. **{len(leads)} viable leads** (bonafide interest + missed follow-up). "
        f"{len(excluded)} excluded after transcript review.",
        "",
        "Only contacts with **bonafide seller/referral intent** and a **real follow-up gap** appear below.",
        "",
        "Each lead includes a **suggested SMS** customized from transcript and contact context.",
        "",
        "| Priority | Name | Phone | Intent | Suggested SMS |",
        "|----------|------|-------|--------|---------------|",
    ]
    for L in leads[:150]:
        sms = (L.get("suggested_sms") or "—").replace("|", "/")
        rg.append(
            f"| {L.get('priority')} | {L.get('contact_name') or '?'} | {L.get('phone') or '—'} | "
            f"{L.get('intent') or '?'} | {sms[:120]} |"
        )
    rg.extend(["", "## Full suggested SMS (copy-paste ready)", ""])
    for L in leads[:50]:
        if L.get("suggested_sms"):
            rg.extend(
                [
                    f"### {L.get('contact_name') or L.get('contact_id')} ({L.get('phone') or 'no phone'})",
                    f"**Intent:** {L.get('intent')} — {L.get('reason', '')[:100]}",
                ]
            )
            if L.get("contact_specific_hook"):
                rg.append(f"**References:** {L.get('contact_specific_hook')}")
            if L.get("what_went_wrong"):
                rg.append(f"**What went wrong:** {L.get('what_went_wrong')}")
            if L.get("process_improvement"):
                rg.append(f"**Future fix:** {L.get('process_improvement')}")
            rg.extend(["", f"> {L.get('suggested_sms')}", ""])
    reengage_path.write_text("\n".join(rg), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "priority", "contact_id", "contact_name", "phone", "email",
                "date_added", "last_activity", "intent", "viability", "intent_summary",
                "reason", "suggested_action", "contact_specific_hook", "suggested_sms",
                "what_went_wrong", "process_improvement",
                "pipeline_name", "stage_name", "tags",
            ],
        )
        w.writeheader()
        for L in leads:
            row = {k: L.get(k) for k in w.fieldnames}
            for k in ("date_added", "last_activity"):
                if row.get(k) and hasattr(row[k], "isoformat"):
                    row[k] = row[k].isoformat()
            w.writerow(row)

    write_telegram_reengage_summary(account, leads, excluded, run_id, today)

    return strat_path, reengage_path


def write_telegram_reengage_summary(
    account: dict[str, Any],
    leads: list[dict[str, Any]],
    excluded: list[dict[str, Any]],
    run_id: int,
    today: str,
) -> Path:
    """Short summary for Telegram — agent reads this file on request (not pre-loaded in chat)."""
    base = OBS / "GHL" / account["obsidian_folder"] / "Recommendations"
    latest = base / "LATEST-REENGAGE-SUMMARY.md"
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_leads = sorted(
        leads,
        key=lambda x: (order.get(x.get("priority", "low"), 9), x.get("contact_name") or ""),
    )
    lines = [
        f"# Re-engage summary — {account['display_name']}",
        "",
        f"**Updated:** {today} | **Audit run:** {run_id}",
        f"**Viable leads:** {len(leads)} | **Excluded:** {len(excluded)}",
        "",
        "Boss: ask for re-engage summary in Telegram — read this file and reply with top priorities + SMS.",
        "",
        "## Top leads (critical / high first)",
        "",
    ]
    for i, L in enumerate(sorted_leads[:12], 1):
        name = L.get("contact_name") or L.get("contact_id") or "?"
        phone = L.get("phone") or "—"
        pri = L.get("priority") or "?"
        intent = L.get("intent") or "?"
        hook = (L.get("contact_specific_hook") or "")[:80]
        sms = (L.get("suggested_sms") or "")[:200]
        lines.extend(
            [
                f"### {i}. [{pri}] {name} ({phone})",
                f"- **Intent:** {intent}",
                f"- **Hook:** {hook or '—'}",
                f"- **Gap:** {(L.get('reason') or '')[:100]}",
                f"- **SMS:** {sms or '—'}",
                "",
            ]
        )
    if len(sorted_leads) > 12:
        lines.append(f"*(+{len(sorted_leads) - 12} more in `{today}-reengage-leads.md`)*")
        lines.append("")

    move_on = [
        x
        for x in excluded
        if x.get("disposition") in (DISPOSITION_MOVE_ON, DISPOSITION_LANDLINE, DISPOSITION_OUTBOUND_ONLY)
    ]
    if move_on:
        lines.extend(["## Move on / landline (do NOT re-engage)", ""])
        for x in move_on[:15]:
            phone = x.get("phone") or "—"
            disp = x.get("disposition") or "?"
            note = (x.get("disposition_note") or x.get("exclude_reason") or "")[:200]
            tags = x.get("ghl_tags_recommended")
            lines.append(
                f"- **{x.get('contact_name') or x.get('contact_id')}** ({phone}) — `{disp}`"
            )
            lines.append(f"  - {note}")
            if tags:
                lines.append(f"  - GHL tags: `{', '.join(tags)}`")
        lines.append("")

    lines.extend(
        [
            "## Agent instructions",
            "",
            "- **Landline / outbound-only:** do not SMS; tag `landline` in GHL and move on.",
            "- **Referral-only / not serious:** note disposition and move on — do not re-engage.",
            "",
            f"- Full report: `/home/node/obsidian/GHL/{account['obsidian_folder']}/Recommendations/{today}-reengage-leads.md`",
            f"- CSV: `.../Recommendations/{today}-reengage-leads.csv`",
            "- Refresh: `python3 /docker/clawsum/scripts/ghl-strategic-audit.py --slug "
            + account["slug"]
            + " --use-llm`",
            "",
        ]
    )
    latest.write_text("\n".join(lines), encoding="utf-8")
    text = latest.read_text(encoding="utf-8")
    ws = Path(f"/docker/clawsum/data/.openclaw/workspace-{account['id']}")
    ws_notes = ws / "notes"
    ws_notes.mkdir(parents=True, exist_ok=True)
    (ws_notes / "LATEST-REENGAGE-SUMMARY.md").write_text(text, encoding="utf-8")
    (ws / "REENGAGE.md").write_text(text, encoding="utf-8")
    (ws / "notes" / "REENGAGE.md").write_text(text, encoding="utf-8")
    return latest


def main() -> None:
    parser = argparse.ArgumentParser(description="Strategic GHL CRM audit")
    default_slug = ghl.accounts()[0]["slug"] if ghl.accounts() else "ghl"
    parser.add_argument("--slug", default=default_slug, help=f"Account slug from ghl-accounts.json (default: {default_slug})")
    parser.add_argument(
        "--vertical",
        choices=[VERTICAL_GENERIC, VERTICAL_REI],
        default=VERTICAL_GENERIC,
        help="Audit lens: generic CRM (default) or rei instance overlay",
    )
    parser.add_argument("--contact-limit", type=int, default=400)
    parser.add_argument("--conversation-limit", type=int, default=150)
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument(
        "--apply-landline-tags",
        action="store_true",
        help="Apply landline/no-sms tags in GHL for detected landlines (Tier B — operator approval)",
    )
    args = parser.parse_args()
    vertical = args.vertical

    account = ghl.account_by_slug(args.slug)
    if not account:
        raise SystemExit(f"Unknown slug: {args.slug}")

    env = load_env()
    pit = env.get(account["env_pit"], "").strip()
    location_id = env.get(account["env_location"], "").strip()
    if not pit or not location_id:
        raise SystemExit("Missing PIT or location ID in .env")

    print(f"=== Strategic audit: {account['display_name']} (vertical={vertical}) ===\n")
    ensure_tables()
    password = sync_db_password(account, env)

    available, tool_names = mcp_tools_list(pit, location_id)
    print(f"MCP tools: {len(available)}")

    loc_data = mcp_tool("locations_get-location", {}, pit, location_id, available)
    location_name = (loc_data.get("location") or loc_data).get("name") if isinstance(loc_data, dict) else account["display_name"]
    if isinstance(loc_data, dict) and loc_data.get("name"):
        location_name = loc_data["name"]

    print("Fetching custom fields...")
    fields = fetch_custom_fields(pit, location_id, available)
    field_recs, missing_fields = analyze_fields(fields, vertical)
    matched = match_fields(fields, vertical)

    print("Fetching pipelines...")
    pipelines = fetch_pipelines(pit, location_id, available)
    pipe_recs, stage_map = analyze_pipelines(pipelines, vertical)

    print(f"Fetching contacts (newest first, limit {args.contact_limit})...")
    contacts = fetch_contacts_recent(pit, location_id, available, args.contact_limit)
    print(f"  {len(contacts)} contacts")
    contacts_by_id = {c["id"]: c for c in contacts if c.get("id")}

    print("Fetching opportunities...")
    opps = fetch_opportunities(pit, location_id, available, min(args.contact_limit, 200))

    conv_limit = args.conversation_limit
    print(f"Fetching conversations (limit {conv_limit})...")
    conversations = fetch_conversations(pit, location_id, available, conv_limit)
    print(f"  {len(conversations)} conversations")

    conv_reviews: list[dict[str, Any]] = []
    contact_profiles: dict[str, dict[str, Any]] = {}
    llm_threads: list[dict[str, Any]] = []
    seen_conv_ids: set[str] = set()
    print("Analyzing conversation messages (SMS + calls + intent)...")
    analyze_conversation_batch(
        conversations,
        pit,
        location_id,
        available,
        contacts_by_id,
        contact_profiles,
        conv_reviews,
        llm_threads,
        seen_conv_ids,
    )
    print(f"  {len(conv_reviews)} conversation gaps after first pass")

    leads, excluded = build_reengage_leads(
        contacts, opps, conv_reviews, contact_profiles, stage_map, pipelines
    )

    if len(leads) < MIN_VIABLE_REENGAGE:
        deeper = min(300, max(conv_limit * 2, 200))
        if deeper > conv_limit:
            print(
                f"Only {len(leads)} viable leads (< {MIN_VIABLE_REENGAGE}) — "
                f"scanning {deeper} conversations (deeper lookback)..."
            )
            more_conversations = fetch_conversations(pit, location_id, available, deeper)
            analyze_conversation_batch(
                more_conversations,
                pit,
                location_id,
                available,
                contacts_by_id,
                contact_profiles,
                conv_reviews,
                llm_threads,
                seen_conv_ids,
                label="deep",
            )
            leads, excluded = build_reengage_leads(
                contacts, opps, conv_reviews, contact_profiles, stage_map, pipelines
            )
            print(f"  After deep scan: {len(leads)} viable, {len(excluded)} excluded")

    landline_candidates = collect_landline_tag_candidates(contact_profiles, contacts_by_id)
    if landline_candidates:
        print(f"Landline / SMS-blocked: {len(landline_candidates)} contacts need GHL landline tag")
        if args.apply_landline_tags:
            applied, tag_errors = apply_landline_tags(
                pit, location_id, available, landline_candidates
            )
            print(f"  Applied landline tags to {applied}/{len(landline_candidates)} contacts")
            for err in tag_errors[:5]:
                print(f"  tag error: {err}")

    now = datetime.now(timezone.utc)
    stale_recent = sum(
        1
        for c in contacts
        if parse_ts(c.get("dateAdded"))
        and (now - parse_ts(c.get("dateAdded"))).days <= 30
        and (now - (
            max(
                filter(
                    None,
                    [
                        parse_ts(c.get("lastActivity")),
                        (contact_profiles.get(c.get("id") or "") or {}).get("last_touch_at"),
                    ],
                ),
                default=parse_ts(c.get("dateAdded")),
            )
        )).days
        >= 7
        and not (contact_profiles.get(c.get("id") or "") or {}).get("worked_lead")
    )
    auto_recs = automation_recommendations(len(conv_reviews), stale_recent, vertical)
    if landline_candidates:
        auto_recs.append(
            {
                "priority": "high",
                "issue": f"{len(landline_candidates)} landline/SMS-blocked numbers in audit",
                "fix": (
                    "Workflow: on SMS delivery error (landline/30006), auto-add tags `landline` + `no-sms`, "
                    "remove from SMS drips, route to call-only queue. "
                    "Run audit with `--apply-landline-tags` to backfill tags."
                ),
            }
        )

    print(f"Re-engage list: {len(leads)} viable leads ({len(excluded)} excluded after review)")

    api_key = env.get("OPENAI_API_KEY", "").strip() or None
    enrich_with_followup_sms(
        leads, conv_reviews, contacts_by_id, contact_profiles, location_name, api_key=api_key, vertical=vertical
    )
    if leads:
        print(f"  Suggested SMS drafted for {len(leads)} leads")

    llm_summary = ""
    if args.use_llm and api_key:
        print("Running LLM conversation analysis...")
        llm_summary = llm_conversation_summary(llm_threads, api_key, vertical)

    summary = (
        f"Strategic audit: {len(leads)} re-engage, {len(excluded)} excluded, {len(conv_reviews)} conv gaps, "
        f"{len(field_recs)+len(pipe_recs)+len(auto_recs)} recommendations"
    )
    run_id = insert_audit_run(account, password, location_id, summary)
    persist_leads(account, password, run_id, leads)
    persist_conv_reviews(account, password, run_id, conv_reviews)

    strat_path, reengage_path = write_reports(
        account, location_name, field_recs, pipe_recs, auto_recs,
        fields, matched, pipelines, leads, excluded, conv_reviews, llm_summary, run_id, vertical,
    )

    print(f"\nStrategic report: {strat_path}")
    print(f"Re-engage list:   {reengage_path}")
    print(f"Postgres run id:  {run_id}")
    print("Done.")


if __name__ == "__main__":
    main()
