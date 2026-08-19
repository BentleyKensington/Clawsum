"""Clustered Hermes / Arcade / Obsidian graph builders for the cockpit Graph deck."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

TOPIC_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("RE", ("avenou", "real estate", "wholesale", "comp", "property", "listing", "seller", "buyer", "rei", "deal")),
    ("GHL", ("ghl", "gohighlevel", "pipeline", "appointment", "crm", "lead")),
    ("Media", ("content", "video", "youtube", "repurpos", "studio", "script", "flyer")),
    ("Legal", ("legal", "llc", "attorney", "compliance")),
    ("Finance", ("bookkeep", "invoice", "revenue", "receivable", "quickbooks", "a/r")),
    ("Growth", ("seo", "ppc", "ads", "funnel", "aeo", "geo")),
    ("Inbox", ("gmail", "email", "oauth", "inbox", "mailbox")),
    ("Platform", ("clawsum", "hermes", "openclaw", "paperclip", "jarvis", "grafana", "vps", "docker")),
    ("Ops", ("cron", "monitor", "alert", "backup", "health")),
]
AGENT_TOPIC = {
    "realestate": "RE",
    "ghl": "GHL",
    "comms": "Media",
    "research": "Growth",
    "planning": "Ops",
    "coding": "Platform",
    "data": "Ops",
    "admin": "Platform",
    "hermes": "Platform",
    "paperclip": "Platform",
}
WIKI_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


def entity_ok(label: str) -> bool:
    s = (label or "").strip()
    if not s or s.lower() in {"unknown", "none", "n/a", "null"}:
        return False
    if len(s) > 48 or s.count(" ") > 6:
        return False
    return True


def topic_of(label: str, source_agent: str = "", fact_type: str = "") -> str:
    blob = f"{label} {source_agent} {fact_type}".lower()
    aid = (source_agent or "").strip().lower()
    if aid in AGENT_TOPIC:
        return AGENT_TOPIC[aid]
    for topic, keys in TOPIC_RULES:
        if any(k in blob for k in keys):
            return topic
    if (fact_type or "").lower() == "project":
        return "Projects"
    return "General"


def _kind_of(label: str, fact_type: str = "") -> str:
    ft = (fact_type or "").lower()
    if ft == "project":
        return "project"
    if ft == "task":
        return "project"
    return "entity"


def clustered_hermes(
    rows: list[dict[str, Any]], *, cluster: str = ""
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """L0 topics always visible; L1 short entities hang off topics. No hub-to-hub filter."""
    want = (cluster or "").strip()
    stats: dict[str, dict[str, Any]] = {}
    pairs: list[tuple[str, str, str, str]] = []

    def bump(label: str, agent: str, fact_type: str) -> str | None:
        key = (label or "").strip()[:80]
        if not entity_ok(key):
            return None
        rec = stats.setdefault(
            key,
            {
                "label": key,
                "degree": 0,
                "topic": topic_of(key, agent, fact_type),
                "kind": _kind_of(key, fact_type),
                "facts": [],
            },
        )
        rec["degree"] += 1
        if rec["kind"] == "entity" and _kind_of(key, fact_type) == "project":
            rec["kind"] = "project"
        return key

    for r in rows:
        subj = str(r.get("subject") or "")
        obj = str(r.get("object") or "")
        pred = str(r.get("predicate") or "related")
        agent = str(r.get("source_agent") or "")
        ft = str(r.get("fact_type") or "")
        a = bump(subj, agent, ft)
        b = bump(obj, agent, ft)
        if a:
            stats[a]["facts"].append(
                {"predicate": pred, "other": obj[:80], "dir": "out", "importance": r.get("importance")}
            )
        if b:
            stats[b]["facts"].append(
                {"predicate": pred, "other": subj[:80], "dir": "in", "importance": r.get("importance")}
            )
        if a and b and a != b:
            pairs.append((a, b, pred, topic_of(a, agent, ft)))

    ranked = sorted(stats.values(), key=lambda x: (-int(x["degree"]), x["label"].lower()))
    if want:
        focus = [e for e in ranked if e["topic"].lower() == want.lower() or e["label"].lower() == want.lower()]
        other = [e for e in ranked if e not in focus]
        chosen = (focus + other)[:80]
    else:
        chosen = ranked[:48]

    chosen_keys = {e["label"] for e in chosen}
    topics_used = sorted({e["topic"] for e in chosen})
    nodes: list[dict[str, Any]] = []
    id_of: dict[str, str] = {}

    def sid(prefix: str, label: str) -> str:
        slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in (label or ""))
        slug = "-".join(part for part in slug.split("-") if part)[:48] or "x"
        return f"{prefix}:{slug}"

    for topic in topics_used:
        nid = sid("t", topic)
        id_of[f"topic::{topic}"] = nid
        members = [e["label"] for e in chosen if e["topic"] == topic]
        nodes.append(
            {
                "id": nid,
                "label": topic,
                "kind": "topic",
                "topic": topic,
                "degree": len(members),
                "facts": [{"predicate": "contains", "other": m, "dir": "out"} for m in members[:12]],
            }
        )

    for ent in chosen:
        nid = sid("e", ent["label"])
        id_of[ent["label"]] = nid
        nodes.append(
            {
                "id": nid,
                "label": ent["label"],
                "kind": ent["kind"],
                "topic": ent["topic"],
                "degree": int(ent["degree"]),
                "facts": (ent["facts"] or [])[:12],
            }
        )

    edges: list[dict[str, Any]] = []
    seen_e: set[tuple[str, str]] = set()

    def add_edge(src: str, dst: str, label: str, kind: str) -> None:
        if not src or not dst or src == dst:
            return
        key = (src, dst)
        if key in seen_e:
            return
        seen_e.add(key)
        edges.append({"source": src, "target": dst, "label": label, "kind": kind})

    for ent in chosen:
        add_edge(id_of[f"topic::{ent['topic']}"], id_of[ent["label"]], "contains", "cluster")

    for a, b, pred, _topic in pairs:
        if a in chosen_keys and b in chosen_keys:
            add_edge(id_of[a], id_of[b], pred, "fact")

    clusters = [
        {
            "id": id_of[f"topic::{t}"],
            "label": t,
            "count": sum(1 for e in chosen if e["topic"] == t),
        }
        for t in topics_used
    ]
    return nodes, edges, clusters


def arcade_status(env_fn: Callable[[str, str], str]) -> dict[str, Any]:
    url = env_fn("ARCADEDB_URL", "http://127.0.0.1:2480").rstrip("/")
    user = env_fn("ARCADEDB_USER", "root") or "root"
    password = env_fn("ARCADEDB_ROOT_PASSWORD", "")
    database = env_fn("ARCADEDB_DATABASE", "clawsum_graph") or "clawsum_graph"
    out: dict[str, Any] = {
        "up": False,
        "studio": url,
        "database": database,
        "count": 0,
        "note": "Arcade Studio is 2D Cytoscape on 127.0.0.1:2480 (not public). Pane shows the Hermes cluster mirror.",
        "nodes": [],
        "edges": [],
    }
    try:
        req = urllib.request.Request(f"{url}/api/v1/ready", method="GET")
        if password:
            token = __import__("base64").b64encode(f"{user}:{password}".encode()).decode()
            req.add_header("Authorization", f"Basic {token}")
        with urllib.request.urlopen(req, timeout=3) as resp:
            out["up"] = resp.status < 400
    except Exception:
        out["up"] = False
        return out
    if not password:
        out["note"] = "Arcade ready, but ARCADEDB_ROOT_PASSWORD unset — showing Hermes mirror."
        return out
    try:
        body = json.dumps(
            {"language": "sql", "command": "SELECT count(*) as n FROM `MemoryEntity`"}
        ).encode()
        req = urllib.request.Request(
            f"{url}/api/v1/command/{database}",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Basic "
                + __import__("base64").b64encode(f"{user}:{password}".encode()).decode(),
            },
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            payload = json.loads(resp.read().decode())
        rows = payload.get("result") if isinstance(payload, dict) else payload
        if isinstance(rows, list) and rows:
            out["count"] = int((rows[0] or {}).get("n") or 0)
        out["note"] = f"Arcade live · {out['count']} MemoryEntity · Studio 2D only at {url}"
    except Exception as exc:
        out["note"] = f"Arcade up; query skipped ({exc}). Hermes mirror shown."
    return out


def _vault_roots() -> list[Path]:
    return [
        Path("/obsidian"),
        Path("/docker/clawsum/obsidian"),
        Path("/home/node/obsidian"),
        Path("/paperclip/obsidian"),
    ]


def _snapshot_paths() -> list[Path]:
    return [
        Path("/paperclip/.hermes/obsidian-graph.json"),
        Path("/docker/clawsum/paperclip-data/.hermes/obsidian-graph.json"),
    ]


def _scan_vault(root: Path, limit: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    scanned = 0

    def nid(label: str, kind: str = "note") -> str:
        key = (label or "").strip()[:80] or "note"
        if key not in seen:
            seen[key] = f"o{len(seen)}"
            nodes.append({"id": seen[key], "label": key, "kind": kind, "degree": 0})
        return seen[key]

    files = sorted(root.rglob("*.md"))
    for path in files[:400]:
        if any(part.startswith(".") for part in path.parts):
            continue
        scanned += 1
        src = nid(path.stem, "note")
        try:
            rel = path.parent.relative_to(root)
            folder = str(rel).replace("\\", "/")
        except Exception:
            folder = ""
        if folder and folder not in {".", ""}:
            hub = nid(folder.split("/")[0], "topic")
            edges.append({"source": hub, "target": src, "label": "folder", "kind": "cluster"})
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[:20000]
        except Exception:
            continue
        for match in WIKI_RE.findall(text):
            dst = nid(match.strip(), "note")
            if src != dst:
                edges.append({"source": src, "target": dst, "label": "wikilink", "kind": "note"})
        if len(nodes) >= limit:
            break
    deg: dict[str, int] = defaultdict(int)
    for e in edges:
        deg[e["source"]] += 1
        deg[e["target"]] += 1
    for n in nodes:
        n["degree"] = deg.get(n["id"], 0)
    return nodes[:limit], edges[:180], scanned


def obsidian_graph(limit: int = 72) -> dict[str, Any]:
    for snap in _snapshot_paths():
        if snap.is_file():
            try:
                data = json.loads(snap.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("nodes"):
                    data.setdefault("note", f"Snapshot {snap}")
                    data["source"] = str(snap)
                    return data
            except Exception:
                continue
    for root in _vault_roots():
        if root.is_dir():
            nodes, edges, scanned = _scan_vault(root, limit)
            return {
                "nodes": nodes,
                "edges": edges,
                "scanned": scanned,
                "note": f"Live vault {root}",
                "source": str(root),
            }
    return {
        "nodes": [],
        "edges": [],
        "scanned": 0,
        "note": "Vault not mounted in paperclip. Run snapshot-obsidian-graph.py on the host.",
        "source": None,
    }


def write_obsidian_snapshot(root: Path, dest: Path, limit: int = 120) -> dict[str, Any]:
    nodes, edges, scanned = _scan_vault(root, limit)
    payload = {
        "nodes": nodes,
        "edges": edges,
        "scanned": scanned,
        "note": f"Snapshot of {root} ({scanned} notes)",
        "source": str(root),
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload), encoding="utf-8")
    return payload


if __name__ == "__main__":
    vault = next((p for p in _vault_roots() if p.is_dir()), Path(os.environ.get("CLAWSUM_OBSIDIAN", "/docker/clawsum/obsidian")))
    dest = Path(os.environ.get("CLAWSUM_OBSIDIAN_GRAPH", "/docker/clawsum/paperclip-data/.hermes/obsidian-graph.json"))
    print(json.dumps(write_obsidian_snapshot(vault, dest), indent=2)[:800])
