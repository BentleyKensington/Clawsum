#!/usr/bin/env python3
"""
Import a ChatGPT data export (ZIP or conversations.json) into ops.* archive tables.

Does NOT promote content into Hermes memory.

Usage:
  python3 import-chatgpt-export.py /path/to/chatgpt-export.zip
  python3 import-chatgpt-export.py /path/to/conversations.json --limit 50
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Need psycopg2: pip install psycopg2-binary", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
IMPORT_DIR = ROOT / "data" / "chatgpt-archive"


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    path = ENV_FILE if ENV_FILE.exists() else Path(__file__).resolve().parents[1] / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        out.setdefault(k, v)
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


SENSITIVE_RE = re.compile(
    r"(api[_-]?key|password|secret|bearer\s+[a-z0-9]|sk-[a-z0-9]{10,}|"
    r"pit-[a-z0-9]+|wire transfer|ssn\b|routing number)",
    re.I,
)


def ts_from_export(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # ChatGPT often uses unix seconds
        if value > 1e12:
            value = value / 1000.0
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def extract_conversations_payload(path: Path) -> tuple[list, str]:
    """Return (conversations_list, raw_uri_note)."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            cand = None
            for n in names:
                if n.endswith("conversations.json") or n == "conversations.json":
                    cand = n
                    break
            if not cand:
                raise SystemExit("ZIP missing conversations.json")
            data = json.loads(zf.read(cand).decode("utf-8", errors="replace"))
            return data if isinstance(data, list) else data.get("conversations", []), f"zip:{path.name}:{cand}"
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if isinstance(data, list):
        return data, f"file:{path.name}"
    if isinstance(data, dict) and "conversations" in data:
        return data["conversations"], f"file:{path.name}"
    raise SystemExit("Unrecognized ChatGPT export JSON shape")


def iter_messages(conv: dict) -> list[dict]:
    """Normalize OpenAI export mapping → ordered message dicts."""
    mapping = conv.get("mapping") or {}
    msgs: list[tuple[float, int, dict]] = []
    order = 0
    for node_id, node in mapping.items():
        message = (node or {}).get("message")
        if not message:
            continue
        author = (message.get("author") or {}).get("role") or message.get("role") or "unknown"
        content = message.get("content")
        text = ""
        if isinstance(content, dict):
            parts = content.get("parts") or []
            text = "\n".join(p for p in parts if isinstance(p, str))
        elif isinstance(content, str):
            text = content
        if not text.strip():
            continue
        create_time = message.get("create_time") or (node or {}).get("create_time")
        ts = 0.0
        if isinstance(create_time, (int, float)):
            ts = float(create_time)
        msgs.append((ts, order, {"role": author, "content": text, "create_time": create_time}))
        order += 1
    # fallback: messages array
    if not msgs and isinstance(conv.get("messages"), list):
        for i, m in enumerate(conv["messages"]):
            if not isinstance(m, dict):
                continue
            text = m.get("content") or m.get("text") or ""
            if isinstance(text, list):
                text = "\n".join(str(x) for x in text)
            msgs.append((0.0, i, {"role": m.get("role", "unknown"), "content": str(text), "create_time": m.get("create_time")}))
    msgs.sort(key=lambda x: (x[0], x[1]))
    return [m for _, _, m in msgs]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", help="Path to ChatGPT export ZIP or conversations.json")
    ap.add_argument("--limit", type=int, default=0, help="Max conversations (0=all)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--source-account", default="chatgpt")
    args = ap.parse_args()

    src = Path(args.path)
    if not src.exists():
        raise SystemExit(f"Not found: {src}")

    conversations, raw_note = extract_conversations_payload(src)
    if args.limit:
        conversations = conversations[: args.limit]
    print(f"Found {len(conversations)} conversations ({raw_note})")

    if args.dry_run:
        for c in conversations[:10]:
            print("-", (c.get("title") or c.get("id") or "?")[:80])
        return

    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    # Keep a copy of the file reference (not necessarily full ZIP duplicate)
    dest_note = IMPORT_DIR / f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    dest_note.write_text(json.dumps({"source": str(src), "raw": raw_note, "count": len(conversations)}), encoding="utf-8")

    conn = connect()
    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO ops.chatgpt_imports (
                  source_account, original_filename, raw_archive_uri, import_status, conversation_count
                ) VALUES (%s, %s, %s, 'parsing', %s)
                RETURNING id
                """,
                (args.source_account, src.name, str(dest_note), len(conversations)),
            )
            import_id = cur.fetchone()["id"]

            stored = 0
            for conv in conversations:
                source_id = str(conv.get("id") or conv.get("conversation_id") or "")
                title = (conv.get("title") or "Untitled").strip() or "Untitled"
                created = ts_from_export(conv.get("create_time"))
                updated = ts_from_export(conv.get("update_time"))
                messages = iter_messages(conv)
                sensitive = any(SENSITIVE_RE.search(m["content"] or "") for m in messages)

                cur.execute(
                    """
                    INSERT INTO ops.conversations (
                      import_id, source_conversation_id, title, created_at_source, updated_at_source,
                      sensitivity_level, message_count, scope, work_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'unknown', 'other')
                    ON CONFLICT (import_id, source_conversation_id) DO UPDATE SET
                      title = EXCLUDED.title,
                      updated_at_source = EXCLUDED.updated_at_source,
                      message_count = EXCLUDED.message_count,
                      updated_at = now()
                    RETURNING id
                    """,
                    (
                        import_id,
                        source_id or f"anon-{stored}",
                        title[:500],
                        created,
                        updated,
                        "flagged" if sensitive else "unknown",
                        len(messages),
                    ),
                )
                conv_id = cur.fetchone()["id"]

                # replace messages for re-import
                cur.execute("DELETE FROM ops.messages WHERE conversation_id = %s", (conv_id,))
                for i, m in enumerate(messages):
                    cur.execute(
                        """
                        INSERT INTO ops.messages (
                          conversation_id, role, content, created_at_source, message_order, contains_sensitive
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            conv_id,
                            m.get("role"),
                            (m.get("content") or "")[:50000],
                            ts_from_export(m.get("create_time")),
                            i,
                            bool(SENSITIVE_RE.search(m.get("content") or "")),
                        ),
                    )
                stored += 1

            cur.execute(
                "UPDATE ops.chatgpt_imports SET import_status = 'parsed', conversation_count = %s WHERE id = %s",
                (stored, import_id),
            )
            cur.execute(
                """
                INSERT INTO ops.audit_logs (actor_type, actor_name, action, tool_name, input_summary, output_summary)
                VALUES ('system', 'import-chatgpt-export', 'archive_imported', 'import-chatgpt-export', %s, %s)
                """,
                (str(src), f"import_id={import_id} conversations={stored}"),
            )

    print(f"OK import_id={import_id} stored={stored}")
    print("Next: python3 scripts/classify-chatgpt-archive.py")
    print("Then:  python3 scripts/link-archive-to-paperclip.py")


if __name__ == "__main__":
    main()
