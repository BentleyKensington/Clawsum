#!/usr/bin/env python3
"""Seed ops.people + ops.places (no secrets). Links Gerald + clawsums@gmail.com mailbox."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Need psycopg2", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"

PEOPLE = [
    {
        "display_name": "Gerald Hennessey",
        "sort_name": "Hennessey, Gerald",
        "kind": "boss",
        "primary_email": None,
        "emails": [],
        "company_name": "Clawsum",
        "title_role": "CEO / Boss",
        "business_slug": "clawsum-platform",
        "tags": ["boss", "gerald"],
        "notes": "Final approver for Tier 2+; Hermes talks to Gerald.",
    },
    {
        "display_name": "Clawsum Admin Mailbox",
        "sort_name": "Clawsum Admin Mailbox",
        "kind": "system",
        "primary_email": "clawsums@gmail.com",
        "emails": ["clawsums@gmail.com"],
        "company_name": "Clawsum",
        "title_role": "Ops inbox",
        "business_slug": "clawsum-platform",
        "tags": ["mailbox", "gmail", "admin"],
        "notes": "Canonical ops inbox — forward external mail here; gmail-sync archives all.",
    },
    {
        "display_name": "WNN Properties",
        "sort_name": "WNN Properties",
        "kind": "org",
        "primary_email": None,
        "emails": [],
        "company_name": "WNN Properties",
        "title_role": "Client org",
        "business_slug": "wnn-client",
        "tags": ["client", "ghl"],
        "notes": "Client cell — people/emails triage to wnn-client.",
    },
]

PLACES = [
    {
        "name": "Clawsum Ops (virtual)",
        "kind": "virtual",
        "timezone": "America/Chicago",
        "business_slug": "clawsum-platform",
        "tags": ["ops", "hermes"],
        "notes": "Primary virtual HQ — Boss CST, VPS remote.",
    },
    {
        "name": "Chicago metro",
        "kind": "region",
        "city": "Chicago",
        "region": "IL",
        "country": "US",
        "timezone": "America/Chicago",
        "business_slug": "personal-admin",
        "tags": ["home_base"],
        "notes": "Default timezone for cron / reminders (America/Chicago).",
    },
]


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    path = ENV_FILE if ENV_FILE.exists() else Path(__file__).resolve().parents[1] / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
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


def upsert_place(cur, pl: dict, biz: dict) -> str | None:
    bid = biz.get(pl["business_slug"])
    cur.execute("SELECT id FROM ops.places WHERE name = %s LIMIT 1", (pl["name"],))
    row = cur.fetchone()
    if row:
        cur.execute(
            """
            UPDATE ops.places SET
              kind = %s,
              city = COALESCE(%s, city),
              region = COALESCE(%s, region),
              country = COALESCE(%s, country),
              timezone = COALESCE(%s, timezone),
              primary_business_id = COALESCE(%s, primary_business_id),
              tags = %s,
              notes = %s,
              updated_at = now()
            WHERE id = %s
            RETURNING id
            """,
            (
                pl["kind"],
                pl.get("city"),
                pl.get("region"),
                pl.get("country", "US"),
                pl.get("timezone"),
                bid,
                pl.get("tags") or [],
                pl.get("notes"),
                row["id"],
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO ops.places (
              name, kind, city, region, country, timezone,
              primary_business_id, tags, notes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                pl["name"],
                pl["kind"],
                pl.get("city"),
                pl.get("region"),
                pl.get("country", "US"),
                pl.get("timezone"),
                bid,
                pl.get("tags") or [],
                pl.get("notes"),
            ),
        )
    out = cur.fetchone()
    return str(out["id"]) if out else None


def upsert_person(cur, pe: dict, biz: dict) -> str | None:
    bid = biz.get(pe["business_slug"])
    emails = list(pe.get("emails") or [])
    if pe.get("primary_email") and pe["primary_email"] not in emails:
        emails = [pe["primary_email"], *emails]

    row = None
    if pe.get("primary_email"):
        cur.execute(
            "SELECT id FROM ops.people WHERE lower(primary_email) = lower(%s) LIMIT 1",
            (pe["primary_email"],),
        )
        row = cur.fetchone()
    if not row:
        cur.execute(
            "SELECT id FROM ops.people WHERE display_name = %s AND kind = %s LIMIT 1",
            (pe["display_name"], pe["kind"]),
        )
        row = cur.fetchone()

    if row:
        cur.execute(
            """
            UPDATE ops.people SET
              display_name = %s, sort_name = %s, kind = %s,
              primary_email = COALESCE(%s, primary_email),
              emails = %s, company_name = %s, title_role = %s,
              primary_business_id = COALESCE(%s, primary_business_id),
              tags = %s, notes = %s, updated_at = now()
            WHERE id = %s
            RETURNING id
            """,
            (
                pe["display_name"],
                pe.get("sort_name"),
                pe["kind"],
                pe.get("primary_email"),
                emails,
                pe.get("company_name"),
                pe.get("title_role"),
                bid,
                pe.get("tags") or [],
                pe.get("notes"),
                row["id"],
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO ops.people (
              display_name, sort_name, kind, primary_email, emails,
              company_name, title_role, primary_business_id, tags, notes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                pe["display_name"],
                pe.get("sort_name"),
                pe["kind"],
                pe.get("primary_email"),
                emails,
                pe.get("company_name"),
                pe.get("title_role"),
                bid,
                pe.get("tags") or [],
                pe.get("notes"),
            ),
        )
    out = cur.fetchone()
    return str(out["id"]) if out else None


def main() -> None:
    conn = connect()
    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, slug FROM ops.businesses")
            biz = {r["slug"]: r["id"] for r in cur.fetchall()}
            if "clawsum-platform" not in biz:
                print(
                    "WARN: clawsum-platform missing — run seed-business-cells.py first",
                    file=sys.stderr,
                )

            place_ids: dict[str, str] = {}
            for pl in PLACES:
                pid = upsert_place(cur, pl, biz)
                if pid:
                    place_ids[pl["name"]] = pid
                    print(f"place {pl['name']}")

            for pe in PEOPLE:
                person_id = upsert_person(cur, pe, biz)
                print(f"person {pe['display_name']} -> {person_id}")
                if pe["kind"] == "boss" and person_id:
                    for pname in ("Clawsum Ops (virtual)", "Chicago metro"):
                        pid = place_ids.get(pname)
                        if not pid:
                            continue
                        cur.execute(
                            """
                            INSERT INTO ops.person_places (person_id, place_id, relation, is_primary)
                            VALUES (%s::uuid, %s::uuid, %s, %s)
                            ON CONFLICT DO NOTHING
                            """,
                            (
                                person_id,
                                pid,
                                "associated",
                                pname == "Chicago metro",
                            ),
                        )

    print(json.dumps({"people": len(PEOPLE), "places": len(PLACES)}, indent=2))


if __name__ == "__main__":
    main()
