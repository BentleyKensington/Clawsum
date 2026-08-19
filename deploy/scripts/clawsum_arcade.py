#!/usr/bin/env python3
"""
ArcadeDB graph mirror for Clawsum contacts / documents / media.

Postgres remains SoR. Arcade stores Person / EmailMessage / MediaObject / Document
vertices and Mentions / Sent / AttachedTo / Knows edges for multi-hop recall.

Env:
  ARCADEDB_URL (default http://127.0.0.1:2480)
  ARCADEDB_DATABASE (default clawsum_graph)
  ARCADEDB_USER (default root)
  ARCADEDB_ROOT_PASSWORD
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _load_file_env() -> dict[str, str]:
    out: dict[str, str] = {}
    env_path = Path("/docker/clawsum/.env")
    if not env_path.is_file():
        return out
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _cfg() -> dict[str, str]:
    file_env = _load_file_env()
    return {
        "url": os.environ.get("ARCADEDB_URL")
        or file_env.get("ARCADEDB_URL")
        or "http://127.0.0.1:2480",
        "database": os.environ.get("ARCADEDB_DATABASE")
        or file_env.get("ARCADEDB_DATABASE")
        or "clawsum_graph",
        "user": os.environ.get("ARCADEDB_USER") or file_env.get("ARCADEDB_USER") or "root",
        "password": os.environ.get("ARCADEDB_ROOT_PASSWORD")
        or file_env.get("ARCADEDB_ROOT_PASSWORD")
        or "",
    }


def _auth(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def command(script: str, *, url: str, database: str, user: str, password: str) -> list:
    endpoint = f"{url.rstrip('/')}/api/v1/command/{database}"
    body = json.dumps({"language": "sql", "command": script}).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": _auth(user, password),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode() if e.fp else str(e)
        raise RuntimeError(f"ArcadeDB HTTP {e.code}: {err}") from e
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"ArcadeDB error: {payload['error']}")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and "result" in payload:
        r = payload["result"]
        return r if isinstance(r, list) else [r]
    return [payload] if payload else []


def ensure_database(url: str, user: str, password: str, database: str) -> None:
    endpoint = f"{url.rstrip('/')}/api/v1/server"
    # ArcadeDB does NOT accept "IF NOT EXISTS" in create database (treats it as name).
    body = json.dumps({"command": f"create database {database}"}).encode()
    req = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": _auth(user, password),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            _ = resp.read()
        return
    except urllib.error.HTTPError as e:
        err = e.read().decode() if e.fp else str(e)
        low = err.lower()
        if "already" in low or "exist" in low or e.code in (400, 409):
            return
        raise RuntimeError(f"Could not ensure ArcadeDB database {database}: {err}") from e


_READY = False


def _ensure_ready() -> dict[str, str]:
    global _READY
    cfg = _cfg()
    if not cfg["password"]:
        raise RuntimeError("ARCADEDB_ROOT_PASSWORD not set")
    if not _READY:
        ensure_database(cfg["url"], cfg["user"], cfg["password"], cfg["database"])
        for vtype in (
            "Person",
            "EmailMessage",
            "MediaObject",
            "Place",
            "Document",
            "SourceChunk",
            "Fact",
            "Episode",
            "MemoryEntity",
        ):
            try:
                command(
                    f"CREATE VERTEX TYPE `{vtype}` IF NOT EXISTS",
                    **{k: cfg[k] for k in ("url", "database", "user", "password")},
                )
            except RuntimeError:
                try:
                    command(
                        f"CREATE DOCUMENT TYPE `{vtype}` IF NOT EXISTS",
                        **{k: cfg[k] for k in ("url", "database", "user", "password")},
                    )
                except RuntimeError:
                    pass
        for etype in (
            "Mentions",
            "Sent",
            "Received",
            "AttachedTo",
            "LocatedAt",
            "Knows",
            "HasChunk",
            "Asserts",
            "About",
            "Supersedes",
        ):
            try:
                command(
                    f"CREATE EDGE TYPE `{etype}` IF NOT EXISTS",
                    **{k: cfg[k] for k in ("url", "database", "user", "password")},
                )
            except RuntimeError:
                pass
        _READY = True
    return cfg


def _cmd(script: str) -> list:
    cfg = _ensure_ready()
    return command(
        script,
        url=cfg["url"],
        database=cfg["database"],
        user=cfg["user"],
        password=cfg["password"],
    )


def _esc(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return json.dumps(str(v), ensure_ascii=False)


def upsert_vertex(vtype: str, clawsum_id: str, props: dict[str, Any]) -> None:
    _ensure_ready()
    fields = {"clawsum_id": clawsum_id, **props}
    try:
        _cmd(f"DELETE FROM `{vtype}` WHERE clawsum_id = {_esc(clawsum_id)}")
    except RuntimeError:
        pass
    sets = ", ".join(f"`{k}` = {_esc(v)}" for k, v in fields.items())
    _cmd(f"INSERT INTO `{vtype}` SET {sets}")


def mirror_person(person: dict[str, Any]) -> None:
    pid = person.get("id")
    if not pid:
        return
    upsert_vertex(
        "Person",
        str(pid),
        {
            "display_name": person.get("display_name") or "",
            "emails": json.dumps(person.get("emails") or []),
            "phones": json.dumps(person.get("phones") or []),
            "source": "postgres_ops_people",
        },
    )


def mirror_email(
    *,
    gmail_id: str,
    subject: str | None,
    from_addr: str | None,
    received_at: str | None,
    person_id: str | None,
) -> None:
    upsert_vertex(
        "EmailMessage",
        gmail_id,
        {
            "subject": subject or "",
            "from_addr": from_addr or "",
            "received_at": received_at or "",
            "person_id": person_id or "",
        },
    )
    if person_id:
        try:
            _cmd(
                f"CREATE EDGE `Sent` FROM "
                f"(SELECT FROM `Person` WHERE clawsum_id = {_esc(person_id)}) "
                f"TO (SELECT FROM `EmailMessage` WHERE clawsum_id = {_esc(gmail_id)})"
            )
        except RuntimeError:
            pass


def mirror_media(
    *,
    media_id: str,
    uri: str,
    kind: str,
    filename: str | None,
    person_id: str | None = None,
    email_gmail_id: str | None = None,
) -> None:
    upsert_vertex(
        "MediaObject",
        media_id,
        {
            "uri": uri,
            "kind": kind,
            "filename": filename or "",
            "person_id": person_id or "",
            "email_gmail_id": email_gmail_id or "",
        },
    )
    if person_id:
        try:
            _cmd(
                f"CREATE EDGE `AttachedTo` FROM "
                f"(SELECT FROM `MediaObject` WHERE clawsum_id = {_esc(media_id)}) "
                f"TO (SELECT FROM `Person` WHERE clawsum_id = {_esc(person_id)})"
            )
        except RuntimeError:
            pass
    if email_gmail_id:
        try:
            _cmd(
                f"CREATE EDGE `AttachedTo` FROM "
                f"(SELECT FROM `MediaObject` WHERE clawsum_id = {_esc(media_id)}) "
                f"TO (SELECT FROM `EmailMessage` WHERE clawsum_id = {_esc(email_gmail_id)})"
            )
        except RuntimeError:
            pass


def link_mentioned(from_person_id: str, to_person_id: str, kind: str = "Knows") -> None:
    if not from_person_id or not to_person_id or from_person_id == to_person_id:
        return
    edge = "Knows" if kind == "Knows" else "Mentions"
    try:
        _cmd(
            f"CREATE EDGE `{edge}` FROM "
            f"(SELECT FROM `Person` WHERE clawsum_id = {_esc(from_person_id)}) "
            f"TO (SELECT FROM `Person` WHERE clawsum_id = {_esc(to_person_id)})"
        )
    except RuntimeError:
        pass


def mirror_document(
    *,
    doc_id: str,
    title: str,
    uri: str | None = None,
    summary: str | None = None,
    person_ids: list[str] | None = None,
) -> None:
    upsert_vertex(
        "Document",
        doc_id,
        {"title": title or "", "uri": uri or "", "summary": (summary or "")[:2000]},
    )
    for pid in person_ids or []:
        try:
            _cmd(
                f"CREATE EDGE `Mentions` FROM "
                f"(SELECT FROM `Document` WHERE clawsum_id = {_esc(doc_id)}) "
                f"TO (SELECT FROM `Person` WHERE clawsum_id = {_esc(pid)})"
            )
        except RuntimeError:
            pass


def _entity_id(name: str, role: str) -> str:
    raw = f"{role}|{(name or '').strip().lower()}"
    import hashlib

    return "ent_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def mirror_memory_entity(name: str, *, kind: str = "entity") -> str:
    eid = _entity_id(name, kind)
    upsert_vertex(
        "MemoryEntity",
        eid,
        {"name": (name or "")[:200], "kind": kind, "source": "memory_facts"},
    )
    return eid


def mirror_memory_fact(fact: dict[str, Any]) -> None:
    """Mirror a Postgres ops.memory_facts row into Arcade Fact + MemoryEntity graph."""
    fid = str(fact.get("id") or "")
    if not fid:
        return
    subject = str(fact.get("subject") or "")
    obj = str(fact.get("object") or "")
    predicate = str(fact.get("predicate") or "")
    upsert_vertex(
        "Fact",
        fid,
        {
            "fact_key": str(fact.get("fact_key") or ""),
            "subject": subject,
            "predicate": predicate,
            "object": obj,
            "fact_type": str(fact.get("fact_type") or ""),
            "importance": str(fact.get("importance") or ""),
            "confidence": str(fact.get("confidence") or ""),
            "status": str(fact.get("status") or "active"),
            "scope": str(fact.get("scope") or ""),
            "source_host": str(fact.get("source_host") or ""),
        },
    )
    if subject:
        sid = mirror_memory_entity(subject, kind="subject")
        try:
            _cmd(
                f"CREATE EDGE `Asserts` FROM "
                f"(SELECT FROM `Fact` WHERE clawsum_id = {_esc(fid)}) "
                f"TO (SELECT FROM `MemoryEntity` WHERE clawsum_id = {_esc(sid)})"
            )
        except RuntimeError:
            pass
    if obj:
        oid = mirror_memory_entity(obj, kind="object")
        try:
            _cmd(
                f"CREATE EDGE `About` FROM "
                f"(SELECT FROM `Fact` WHERE clawsum_id = {_esc(fid)}) "
                f"TO (SELECT FROM `MemoryEntity` WHERE clawsum_id = {_esc(oid)})"
            )
        except RuntimeError:
            pass


def mirror_memory_episode(episode: dict[str, Any]) -> None:
    eid = str(episode.get("id") or "")
    if not eid:
        return
    upsert_vertex(
        "Episode",
        eid,
        {
            "title": str(episode.get("title") or ""),
            "summary": str(episode.get("summary") or "")[:2000],
            "outcome": str(episode.get("outcome") or "")[:1000],
            "result_state": str(episode.get("result_state") or ""),
            "importance": str(episode.get("importance") or ""),
            "scope": str(episode.get("scope") or ""),
            "source_host": str(episode.get("source_host") or ""),
        },
    )


def link_supersedes(winner_id: str, loser_id: str) -> None:
    """Edge: winner Fact Supersedes loser Fact (dreaming historization)."""
    if not winner_id or not loser_id or winner_id == loser_id:
        return
    try:
        _cmd(
            f"CREATE EDGE `Supersedes` FROM "
            f"(SELECT FROM `Fact` WHERE clawsum_id = {_esc(winner_id)}) "
            f"TO (SELECT FROM `Fact` WHERE clawsum_id = {_esc(loser_id)})"
        )
    except RuntimeError:
        pass
