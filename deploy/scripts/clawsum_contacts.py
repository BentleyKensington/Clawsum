#!/usr/bin/env python3
"""
Shared contact upsert + extraction for Clawsum.

Postgres ops.people is system of record. ArcadeDB Person vertices + edges are
mirrored best-effort for relationship recall.

Usage:
  from clawsum_contacts import upsert_person, extract_contacts_from_text, upsert_from_email_headers
"""
from __future__ import annotations

import re
import sys
from email.utils import getaddresses, parseaddr
from typing import Any

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
# US-ish phones; normalized to digits (10–15)
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s\-.]*)?(?:\(?\d{3}\)?[\s\-.]*)\d{3}[\s\-.]*\d{4}(?!\d)"
)


def _norm_email(v: str | None) -> str | None:
    if not v:
        return None
    e = v.strip().lower()
    if not e or "@" not in e:
        return None
    return e[:320]


def _norm_phone(v: str | None) -> str | None:
    if not v:
        return None
    digits = re.sub(r"\D", "", v)
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) < 10 or len(digits) > 15:
        return None
    return digits


def _merge_unique(existing: list | None, incoming: list | None) -> list:
    out: list[str] = []
    seen: set[str] = set()
    for item in list(existing or []) + list(incoming or []):
        if item is None:
            continue
        s = str(item).strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def _better_name(current: str | None, candidate: str | None, email: str | None) -> str:
    cur = (current or "").strip()
    cand = (candidate or "").strip()
    em = (email or "").strip().lower()
    if cand and "@" not in cand and cand.lower() != em and len(cand) > 1:
        if not cur or "@" in cur or cur.lower() == em or len(cand) > len(cur):
            return cand[:200]
    return (cur or cand or em or "Unknown")[:200]


def extract_emails(text: str) -> list[str]:
    found = []
    for m in EMAIL_RE.findall(text or ""):
        e = _norm_email(m)
        if e and e not in found:
            found.append(e)
    return found


def extract_phones(text: str) -> list[str]:
    found = []
    for m in PHONE_RE.findall(text or ""):
        p = _norm_phone(m)
        if p and p not in found:
            found.append(p)
    return found


def extract_contacts_from_text(text: str) -> dict[str, list[str]]:
    return {"emails": extract_emails(text), "phones": extract_phones(text)}


def parse_address_list(header_value: str) -> list[tuple[str, str]]:
    """Return [(display_name, email), ...] from a From/To/Cc header."""
    if not header_value:
        return []
    out = []
    for name, email in getaddresses([header_value]):
        e = _norm_email(email)
        if not e:
            continue
        out.append(((name or "").strip(), e))
    return out


def find_person_id(cur, emails: list[str] | None = None, phones: list[str] | None = None):
    emails = [_norm_email(e) for e in (emails or []) if _norm_email(e)]
    phones = [_norm_phone(p) for p in (phones or []) if _norm_phone(p)]
    for e in emails:
        cur.execute(
            """
            SELECT id FROM ops.people
            WHERE lower(primary_email) = %s
               OR %s = ANY (SELECT lower(x) FROM unnest(COALESCE(emails, '{}')) AS x)
            LIMIT 1
            """,
            (e, e),
        )
        row = cur.fetchone()
        if row:
            return row["id"] if isinstance(row, dict) else row[0]
    for p in phones:
        cur.execute(
            """
            SELECT id FROM ops.people
            WHERE %s = ANY (COALESCE(phones, '{}'))
            LIMIT 1
            """,
            (p,),
        )
        row = cur.fetchone()
        if row:
            return row["id"] if isinstance(row, dict) else row[0]
    return None


def upsert_person(
    cur,
    *,
    display_name: str | None = None,
    emails: list[str] | None = None,
    phones: list[str] | None = None,
    tags: list[str] | None = None,
    kind: str = "contact",
    company_name: str | None = None,
    title_role: str | None = None,
    notes: str | None = None,
    business_id=None,
    source: str = "auto",
) -> dict[str, Any]:
    """Merge contact into ops.people. Returns {id, created, emails, phones}."""
    norm_emails = []
    for e in emails or []:
        ne = _norm_email(e)
        if ne and ne not in norm_emails:
            norm_emails.append(ne)
    norm_phones = []
    for p in phones or []:
        np = _norm_phone(p)
        if np and np not in norm_phones:
            norm_phones.append(np)
    if not norm_emails and not norm_phones and not (display_name or "").strip():
        return {"id": None, "created": False, "emails": [], "phones": []}

    existing_id = find_person_id(cur, norm_emails, norm_phones)
    tag_list = list(tags or [])
    if source and f"auto_from_{source}" not in tag_list and source != "seed":
        tag_list.append(f"auto_from_{source}")

    if existing_id:
        cur.execute(
            """
            SELECT id, display_name, primary_email, emails, phones, tags,
                   company_name, title_role, notes, kind, primary_business_id
            FROM ops.people WHERE id = %s
            """,
            (existing_id,),
        )
        raw = cur.fetchone()
        if isinstance(raw, dict):
            row = dict(raw)
        else:
            row = {
                "id": raw[0],
                "display_name": raw[1],
                "primary_email": raw[2],
                "emails": raw[3],
                "phones": raw[4],
                "tags": raw[5],
                "company_name": raw[6],
                "title_role": raw[7],
                "notes": raw[8],
                "kind": raw[9],
                "primary_business_id": raw[10],
            }
        merged_emails = _merge_unique(row.get("emails"), norm_emails)
        primary = _norm_email(row.get("primary_email")) or (merged_emails[0] if merged_emails else None)
        if primary and primary not in merged_emails:
            merged_emails = [primary] + merged_emails
        merged_phones = _merge_unique(row.get("phones"), norm_phones)
        merged_tags = _merge_unique(row.get("tags"), tag_list)
        name = _better_name(row.get("display_name"), display_name, primary)
        note_val = row.get("notes") or ""
        if notes and notes not in note_val:
            note_val = (note_val + ("\n" if note_val else "") + notes)[:4000]
        cur.execute(
            """
            UPDATE ops.people SET
              display_name = %s,
              primary_email = COALESCE(%s, primary_email),
              emails = %s,
              phones = %s,
              tags = %s,
              company_name = COALESCE(%s, company_name),
              title_role = COALESCE(%s, title_role),
              notes = %s,
              primary_business_id = COALESCE(primary_business_id, %s),
              updated_at = now()
            WHERE id = %s
            RETURNING id
            """,
            (
                name,
                primary,
                merged_emails,
                merged_phones,
                merged_tags,
                company_name,
                title_role,
                note_val or None,
                business_id,
                existing_id,
            ),
        )
        out = cur.fetchone()
        pid = str(out["id"] if isinstance(out, dict) else out[0])
        result = {
            "id": pid,
            "created": False,
            "emails": merged_emails,
            "phones": merged_phones,
            "display_name": name,
        }
    else:
        primary = norm_emails[0] if norm_emails else None
        name = _better_name(None, display_name, primary)
        cur.execute(
            """
            INSERT INTO ops.people (
              display_name, kind, primary_email, emails, phones,
              company_name, title_role, primary_business_id, tags, notes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                name,
                kind if kind in (
                    "contact", "boss", "teammate", "vendor", "client", "lead", "org", "system"
                ) else "contact",
                primary,
                norm_emails,
                norm_phones,
                company_name,
                title_role,
                business_id,
                tag_list,
                notes,
            ),
        )
        out = cur.fetchone()
        pid = str(out["id"] if isinstance(out, dict) else out[0])
        result = {
            "id": pid,
            "created": True,
            "emails": norm_emails,
            "phones": norm_phones,
            "display_name": name,
        }

    # Best-effort Arcade mirror (never fail the PG write)
    try:
        from clawsum_arcade import mirror_person

        mirror_person(result)
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: arcade mirror person failed: {exc}", file=sys.stderr)
    return result


def upsert_from_email_headers(
    cur,
    *,
    from_addr: str = "",
    to_addrs: str = "",
    cc_addrs: str = "",
    body_text: str = "",
    business_id=None,
    source: str = "gmail",
) -> list[dict[str, Any]]:
    """Upsert From (primary) + To/Cc + body-extracted contacts. Returns people touched."""
    touched: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _touch(name: str | None, email: str | None, phones: list[str] | None = None, tag: str = "email_party"):
        r = upsert_person(
            cur,
            display_name=name,
            emails=[email] if email else [],
            phones=phones or [],
            tags=[tag, source],
            business_id=business_id,
            source=source,
        )
        if r.get("id") and r["id"] not in seen:
            seen.add(r["id"])
            touched.append(r)

    for name, email in parse_address_list(from_addr):
        _touch(name, email, tag="email_from")
    for name, email in parse_address_list(to_addrs) + parse_address_list(cc_addrs):
        _touch(name, email, tag="email_recipient")

    extracted = extract_contacts_from_text(body_text or "")
    # Phones without email → standalone upsert by phone
    for phone in extracted["phones"]:
        r = upsert_person(
            cur,
            phones=[phone],
            tags=["extracted_phone", source],
            business_id=business_id,
            source=source,
            notes=f"Phone extracted from {source}",
        )
        if r.get("id") and r["id"] not in seen:
            seen.add(r["id"])
            touched.append(r)
    for email in extracted["emails"]:
        # skip if already handled via headers
        if any(email in (t.get("emails") or []) for t in touched):
            continue
        _touch(None, email, tag="extracted_email")

    # Link From person → mentioned emails in Arcade
    if touched:
        try:
            from clawsum_arcade import link_mentioned

            primary = touched[0]
            for other in touched[1:6]:
                link_mentioned(primary["id"], other["id"], kind="emailed_with")
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: arcade edge failed: {exc}", file=sys.stderr)
    return touched


# Back-compat for gmail-inbox-review
def ensure_person(cur, email: str, from_display: str, business_id) -> str | None:
    name, addr = parseaddr(from_display or "")
    em = _norm_email(email) or _norm_email(addr)
    r = upsert_person(
        cur,
        display_name=name or from_display,
        emails=[em] if em else [],
        business_id=business_id,
        source="gmail",
        tags=["auto_from_gmail"],
    )
    return r.get("id")
