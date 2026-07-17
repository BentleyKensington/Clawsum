#!/usr/bin/env python3
"""
Upsert JSON records into ArcadeDB with schema-on-arrival.

- Creates database clawsum_graph if missing
- CREATE DOCUMENT TYPE <Type> IF NOT EXISTS
- CREATE PROPERTY <Type>.<field> <TYPE> IF NOT EXISTS (inferred from JSON)
- INSERT via SQL CONTENT

Usage (on VPS):
  export ARCADEDB_ROOT_PASSWORD=...
  python3 arcadedb-ingest.py --file records.jsonl
  python3 arcadedb-ingest.py --json '{"_type":"Listing","id":"123","address":"1 Main"}'

JSONL/JSON rules:
  - Required: "_type" (document type name, e.g. Listing, Comp, SourceChunk)
  - Optional: "_id" for upsert key (stored as property clawsum_id)
  - Other keys become properties (nested dict/list → JSON string)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_URL = os.environ.get("ARCADEDB_URL", "http://127.0.0.1:2480")
DEFAULT_DB = os.environ.get("ARCADEDB_DATABASE", "clawsum_graph")
DEFAULT_USER = os.environ.get("ARCADEDB_USER", "root")
DEFAULT_PASSWORD = os.environ.get("ARCADEDB_ROOT_PASSWORD", "")

# JSON value type → ArcadeDB property type (simple inference)
_TYPE_MAP = {
    bool: "BOOLEAN",
    int: "LONG",
    float: "DOUBLE",
    str: "STRING",
}


def _auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def command(
    script: str,
    *,
    url: str,
    database: str,
    user: str,
    password: str,
) -> list[dict]:
    if not password:
        raise SystemExit("Set ARCADEDB_ROOT_PASSWORD in the environment")
    endpoint = f"{url.rstrip('/')}/api/v1/command/{database}"
    body = json.dumps({"language": "sql", "command": script}).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": _auth_header(user, password),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode() if e.fp else str(e)
        raise SystemExit(f"ArcadeDB HTTP {e.code}: {err}") from e
    if isinstance(payload, dict) and payload.get("error"):
        raise SystemExit(f"ArcadeDB error: {payload['error']}")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and "result" in payload:
        return payload["result"] if isinstance(payload["result"], list) else [payload["result"]]
    return [payload] if payload else []


def ensure_database(url: str, user: str, password: str, database: str) -> None:
    # Server-level: create DB if not exists
    endpoint = f"{url.rstrip('/')}/api/v1/server"
    body = json.dumps(
        {"command": f"create database {database} if not exists"}
    ).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": _auth_header(user, password),
        },
    )
    try:
        urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError:
        # Some versions use SQL against default db
        command(
            f"CREATE DATABASE {database} IF NOT EXISTS",
            url=url,
            database=database,
            user=user,
            password=password,
        )


def infer_property_type(value: Any) -> str:
    if value is None:
        return "STRING"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "LONG"
    if isinstance(value, float):
        return "DOUBLE"
    if isinstance(value, (list, dict)):
        return "STRING"  # store JSON-encoded in STRING field
    return "STRING"


def normalize_record(raw: dict) -> tuple[str, dict]:
    doc_type = raw.get("_type") or raw.get("type")
    if not doc_type:
        raise ValueError('Record missing "_type" (e.g. Listing, Comp)')
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k in ("_type", "type"):
            continue
        if k == "_id":
            out["clawsum_id"] = str(v)
            continue
        if isinstance(v, (dict, list)):
            out[k] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = v
    return str(doc_type), out


def ensure_type_and_properties(
    doc_type: str,
    fields: dict[str, Any],
    *,
    url: str,
    database: str,
    user: str,
    password: str,
) -> None:
    command(
        f'CREATE DOCUMENT TYPE "{doc_type}" IF NOT EXISTS',
        url=url,
        database=database,
        user=user,
        password=password,
    )
    for name, value in fields.items():
        if name.startswith("@"):  # reserved
            continue
        arcade_type = infer_property_type(value)
        safe = name.replace('"', "")
        try:
            command(
                f'CREATE PROPERTY "{doc_type}"."{safe}" {arcade_type} IF NOT EXISTS',
                url=url,
                database=database,
                user=user,
                password=password,
            )
        except SystemExit:
            # Older builds may lack IF NOT EXISTS on PROPERTY — ignore duplicate
            try:
                command(
                    f'CREATE PROPERTY "{doc_type}"."{safe}" {arcade_type}',
                    url=url,
                    database=database,
                    user=user,
                    password=password,
                )
            except SystemExit:
                pass


def insert_record(
    doc_type: str,
    fields: dict[str, Any],
    *,
    url: str,
    database: str,
    user: str,
    password: str,
) -> None:
    content = json.dumps(fields, ensure_ascii=False)
    # CONTENT insert; schemaless-friendly once type exists
    command(
        f'INSERT INTO "{doc_type}" CONTENT {content}',
        url=url,
        database=database,
        user=user,
        password=password,
    )


def load_records(path: str | None, inline: str | None) -> list[dict]:
    if inline:
        return [json.loads(inline)]
    if not path:
        raise SystemExit("Provide --file or --json")
    records: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def main() -> None:
    p = argparse.ArgumentParser(description="ArcadeDB schema-on-arrival ingest")
    p.add_argument("--file", help="JSONL file (one object per line)")
    p.add_argument("--json", help="Single JSON object")
    p.add_argument("--url", default=DEFAULT_URL)
    p.add_argument("--database", default=DEFAULT_DB)
    p.add_argument("--user", default=DEFAULT_USER)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    password = DEFAULT_PASSWORD
    records = load_records(args.file, args.json)
    if not records:
        print("No records", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        for r in records:
            t, f = normalize_record(r)
            print(f"would ingest type={t} fields={list(f.keys())}")
        return

    ensure_database(args.url, args.user, password, args.database)

    for raw in records:
        doc_type, fields = normalize_record(raw)
        ensure_type_and_properties(
            doc_type,
            fields,
            url=args.url,
            database=args.database,
            user=args.user,
            password=password,
        )
        insert_record(
            doc_type,
            fields,
            url=args.url,
            database=args.database,
            user=args.user,
            password=password,
        )
        print(f"OK {doc_type} clawsum_id={fields.get('clawsum_id', '-')}")


if __name__ == "__main__":
    main()
