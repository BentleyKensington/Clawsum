#!/usr/bin/env python3
"""
Read-only GHL audit via official MCP → Postgres findings + Obsidian report.

Usage:
  python3 ghl-audit-readonly.py --slug ghl
  python3 ghl-audit-readonly.py --slug ghl --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ghl_accounts as ghl

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
OBS = ROOT / "obsidian"
GATEWAY_JS = SCRIPT_DIR / "ghl_mcp_gateway.js"
GATEWAY_JS_CONTAINER = "/home/node/obsidian/_tools/ghl_mcp_gateway.js"
AUDIT_SQL = ROOT / "postgres-init" / "08-ghl-audit-tables.sql"

READ_TOOLS = [
    ("locations_get-location", {}),
    ("locations_get-custom-fields", {}),
    ("opportunities_get-pipelines", {}),
    ("contacts_get-contacts", {"limit": 100}),
    ("opportunities_search-opportunity", {"limit": 100}),
    ("conversations_search-conversation", {"limit": 50}),
]

TZ = ZoneInfo("America/Chicago")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def ensure_audit_tables() -> None:
    sql_path = AUDIT_SQL if AUDIT_SQL.exists() else (
        Path(__file__).resolve().parent.parent / "postgres-init" / "08-ghl-audit-tables.sql"
    )
    if not sql_path.exists():
        raise SystemExit(f"Missing {sql_path}")
    subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "clawsum-postgres-1",
            "psql",
            "-U",
            "clawsum",
            "-d",
            "ghl",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=sql_path.read_bytes(),
        check=True,
    )


def sync_db_password(account: dict[str, Any], env: dict[str, str]) -> str:
    pw = env.get(account["env_db_password"], "").strip()
    if not pw:
        raise SystemExit(f"Missing {account['env_db_password']} in .env")
    role = ghl.db_role_for(account)
    safe = pw.replace("'", "''")
    subprocess.run(
        [
            "docker",
            "exec",
            "clawsum-postgres-1",
            "psql",
            "-U",
            "clawsum",
            "-d",
            "ghl",
            "-c",
            f"ALTER ROLE {role} PASSWORD '{safe}'; "
            f"GRANT CREATE ON SCHEMA {account['schema_prefix']} TO {role};",
        ],
        check=True,
        capture_output=True,
    )
    return pw


def psql_as_account(account: dict[str, Any], password: str, sql: str) -> str:
    env_pg = {**os.environ, "PGPASSWORD": password}
    role = ghl.db_role_for(account)
    out = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "clawsum-postgres-1",
            "psql",
            "-U",
            role,
            "-d",
            "ghl",
            "-v",
            "ON_ERROR_STOP=1",
            "-tA",
        ],
        input=sql.encode(),
        capture_output=True,
        env=env_pg,
        text=False,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.decode()[:500])
    return out.stdout.decode()


def ensure_gateway_js() -> tuple[str, Path]:
    src = GATEWAY_JS if GATEWAY_JS.exists() else SCRIPT_DIR / "ghl_mcp_gateway.js"
    dest = OBS / "_tools" / "ghl_mcp_gateway.js"
    out_host = OBS / "_tools" / "mcp_out.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    subprocess.run(["chown", "-R", "1000:1000", str(dest.parent)], check=False)
    return GATEWAY_JS_CONTAINER, out_host


def mcp_gateway(cmd: str, *args: str, pit: str, location_id: str) -> dict[str, Any]:
    js_in_container, out_host = ensure_gateway_js()
    out_container = "/home/node/obsidian/_tools/mcp_out.json"
    proc = subprocess.run(
        [
            "docker",
            "exec",
            "-e",
            f"GHL_PIT={pit}",
            "-e",
            f"GHL_LOCATION_ID={location_id}",
            "-e",
            f"GHL_MCP_OUTFILE={out_container}",
            "clawsum-openclaw-gateway-1",
            "node",
            js_in_container,
            cmd,
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        raise RuntimeError(f"MCP gateway failed: {proc.stderr[:400]}")
    meta = {}
    try:
        meta = json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        pass
    if out_host.exists():
        try:
            return json.loads(out_host.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"MCP outfile bad JSON: {e}") from e
    try:
        return json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"MCP gateway bad JSON: {proc.stdout[:300]} ({e})") from e


def extract_tool_result(mcp_resp: dict[str, Any]) -> Any:
    parsed = mcp_resp.get("parsed") or {}
    if isinstance(parsed, dict):
        if "result" in parsed:
            return parsed["result"]
        if "error" in parsed:
            return {"_error": parsed["error"]}
        if "raw" in parsed:
            return parsed
    return parsed


def unwrap_content(data: Any) -> Any:
    """MCP tools often return { content: [{type,text}] }."""
    if not isinstance(data, dict):
        return data
    content = data.get("content")
    if isinstance(content, list) and content:
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                texts.append(item["text"])
        if texts:
            joined = "\n".join(texts)
            try:
                return json.loads(joined)
            except json.JSONDecodeError:
                return joined
    return data


def tool_names_from_list(mcp_list: dict[str, Any]) -> list[str]:
    if isinstance(mcp_list.get("toolNames"), list):
        return [str(x) for x in mcp_list["toolNames"]]
    result = extract_tool_result(mcp_list)
    result = unwrap_content(result)
    if isinstance(result, dict) and "tools" in result:
        return [t.get("name", "") for t in result["tools"] if isinstance(t, dict)]
    return []


def call_read_tool(
    name: str,
    arguments: dict[str, Any],
    pit: str,
    location_id: str,
    available: set[str],
) -> tuple[str, Any]:
    if name not in available:
        return name, {"_skipped": "tool not in PIT scopes / tools/list"}
    args_json = json.dumps(arguments)
    resp = mcp_gateway("call", name, args_json, pit=pit, location_id=location_id)
    if not resp.get("ok"):
        return name, {"_error": resp.get("parsed") or resp.get("text", "")[:500]}
    if resp.get("compact") is not None:
        return name, resp["compact"]
    data = unwrap_content(extract_tool_result(resp))
    return name, data


def as_list(obj: Any) -> list[Any]:
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in ("contacts", "opportunities", "pipelines", "conversations", "data", "items"):
            if isinstance(obj.get(key), list):
                return obj[key]
    return []


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


def analyze(
    account: dict[str, Any],
    tool_results: dict[str, Any],
    available_tools: list[str],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    schema = account["schema_prefix"]

    findings.append(
        {
            "category": "inventory",
            "severity": "info",
            "title": "MCP tools available",
            "detail": f"{len(available_tools)} read tools exposed for {account['display_name']}",
            "recommendation": "Confirm PIT scopes include contacts, opportunities, conversations, locations.",
            "metric_value": len(available_tools),
        }
    )

    loc = tool_results.get("locations_get-location")
    if isinstance(loc, dict) and not loc.get("_error") and not loc.get("_skipped"):
        loc_name = (
            loc.get("name")
            or (loc.get("location") or {}).get("name")
            or (loc.get("location") or {}).get("id")
            or "unknown"
        )
        findings.append(
            {
                "category": "location",
                "severity": "info",
                "title": "Location verified",
                "detail": f"Connected to location: {loc_name}",
                "ghl_entity_type": "location",
            }
        )

    pipelines_raw = tool_results.get("opportunities_get-pipelines")
    pipelines = as_list(pipelines_raw)
    if isinstance(pipelines_raw, dict) and pipelines_raw.get("pipelines"):
        pipelines = pipelines_raw["pipelines"]
    if isinstance(pipelines_raw, dict) and pipelines_raw.get("_error"):
        findings.append(
            {
                "category": "pipeline",
                "severity": "medium",
                "title": "Could not fetch pipelines",
                "detail": str(pipelines_raw.get("_error"))[:500],
                "recommendation": "Add opportunities.readonly scope to PIT.",
            }
        )
    else:
        findings.append(
            {
                "category": "pipeline",
                "severity": "info",
                "title": f"Pipeline inventory ({len(pipelines)} pipelines)",
                "detail": ", ".join(
                    (p.get("name") or p.get("id") or "?") for p in pipelines[:15]
                )
                or "No pipelines returned",
                "metric_value": len(pipelines),
            }
        )

    contacts_raw = tool_results.get("contacts_get-contacts")
    contacts = as_list(contacts_raw)
    if isinstance(contacts_raw, dict) and contacts_raw.get("contacts"):
        contacts = contacts_raw["contacts"]
    if not isinstance(contacts_raw, dict) or not contacts_raw.get("_error"):
        stale_30 = 0
        stale_90 = 0
        now = datetime.now(timezone.utc)
        for c in contacts:
            if not isinstance(c, dict):
                continue
            ts = parse_ts(
                c.get("lastActivity")
                or c.get("dateUpdated")
                or c.get("updatedAt")
                or c.get("lastUpdated")
            )
            if ts and (now - ts).days >= 30:
                stale_30 += 1
            if ts and (now - ts).days >= 90:
                stale_90 += 1
        findings.append(
            {
                "category": "contact_health",
                "severity": "info",
                "title": f"Contact sample ({len(contacts)} in first page)",
                "detail": f"Stale ≥30d: {stale_30}, stale ≥90d: {stale_90} (sample only)",
                "metric_value": len(contacts),
            }
        )
        if stale_90 >= 5:
            findings.append(
                {
                    "category": "contact_health",
                    "severity": "high",
                    "title": "Many stale contacts in sample",
                    "detail": f"{stale_90} contacts with no activity ≥90 days (first {len(contacts)} fetched)",
                    "recommendation": "Review re-engagement workflow and lead nurture automations.",
                    "metric_value": stale_90,
                }
            )

    opps_raw = tool_results.get("opportunities_search-opportunity")
    opps = as_list(opps_raw)
    if isinstance(opps_raw, dict) and opps_raw.get("opportunities"):
        opps = opps_raw["opportunities"]
    if not isinstance(opps_raw, dict) or not opps_raw.get("_error"):
        open_opps = [o for o in opps if isinstance(o, dict) and (o.get("status") or "").lower() != "won"]
        findings.append(
            {
                "category": "opportunity",
                "severity": "info",
                "title": f"Opportunity sample ({len(opps)} rows)",
                "detail": f"Non-won in sample: {len(open_opps)}",
                "metric_value": len(opps),
            }
        )

    conv_raw = tool_results.get("conversations_search-conversation")
    convs = as_list(conv_raw)
    if isinstance(conv_raw, dict) and conv_raw.get("conversations"):
        convs = conv_raw["conversations"]
    if isinstance(conv_raw, dict) and conv_raw.get("_error"):
        findings.append(
            {
                "category": "conversation",
                "severity": "low",
                "title": "Conversations not fetched",
                "detail": str(conv_raw.get("_error"))[:300],
                "recommendation": "Add conversations.readonly scope if inbox audit is needed.",
            }
        )
    elif convs:
        findings.append(
            {
                "category": "conversation",
                "severity": "info",
                "title": f"Conversation sample ({len(convs)} threads)",
                "detail": "Review unworked inbound threads manually in GHL UI.",
                "metric_value": len(convs),
            }
        )

    custom = tool_results.get("locations_get-custom-fields")
    if isinstance(custom, dict) and not custom.get("_error"):
        fields = custom.get("customFields") or as_list(custom)
        findings.append(
            {
                "category": "custom_fields",
                "severity": "info",
                "title": f"Custom fields ({len(fields)})",
                "detail": "Document REI-specific fields in account WORKFLOWS.md after Boss review.",
                "metric_value": len(fields),
            }
        )

    findings.append(
        {
            "category": "automation",
            "severity": "medium",
            "title": "Workflow inventory not available via official MCP v1",
            "detail": "Official GHL MCP (36 tools) does not expose workflow list yet.",
            "recommendation": "Map automations manually in GHL UI or wait for MCP workflow tools on roadmap.",
        }
    )

    return findings


def sql_quote(val: str | None) -> str:
    if val is None:
        return "NULL"
    return "'" + val.replace("'", "''") + "'"


def insert_audit(
    account: dict[str, Any],
    password: str,
    location_id: str,
    findings: list[dict[str, Any]],
    tool_calls: int,
    available_tools: list[str],
    obsidian_rel: str,
    dry_run: bool,
) -> int | None:
    if dry_run:
        print(f"DRY-RUN: would insert {len(findings)} findings")
        return None

    schema = account["schema_prefix"]
    slug = account["slug"]
    summary = f"{len(findings)} findings — read-only audit"
    tools_json = json.dumps(available_tools)

    run_id_s = psql_as_account(
        account,
        password,
        f"""
INSERT INTO {schema}.audit_runs (slug, location_id, status, summary, tool_calls, obsidian_path, raw_tools, finished_at)
VALUES ({sql_quote(slug)}, {sql_quote(location_id)}, 'completed', {sql_quote(summary)}, {tool_calls}, {sql_quote(obsidian_rel)}, {sql_quote(tools_json)}::jsonb, now())
RETURNING id;
""",
    )
    run_id = int(run_id_s.strip().splitlines()[0])

    for f in findings:
        psql_as_account(
            account,
            password,
            f"""
INSERT INTO {schema}.findings (
  audit_run_id, category, severity, title, detail, recommendation,
  ghl_entity_type, ghl_entity_id, metric_value
) VALUES (
  {run_id},
  {sql_quote(f.get('category'))},
  {sql_quote(f.get('severity', 'info'))},
  {sql_quote(f.get('title'))},
  {sql_quote(f.get('detail'))},
  {sql_quote(f.get('recommendation'))},
  {sql_quote(f.get('ghl_entity_type'))},
  {sql_quote(f.get('ghl_entity_id'))},
  {f.get('metric_value') if f.get('metric_value') is not None else 'NULL'}
);
""",
        )
    return run_id


def write_obsidian(
    account: dict[str, Any],
    findings: list[dict[str, Any]],
    tool_results: dict[str, Any],
    available_tools: list[str],
    run_id: int | None,
) -> Path:
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    folder = OBS / "GHL" / account["obsidian_folder"] / "Audits"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{today}-automation-review.md"

    lines = [
        f"# GHL audit — {account['display_name']}",
        "",
        f"- **Date:** {today}",
        f"- **Account:** `{account['id']}`",
        f"- **Audit run ID:** {run_id or 'dry-run'}",
        f"- **Mode:** read-only (MCP)",
        "",
        "## Summary",
        "",
        f"- MCP tools available: **{len(available_tools)}**",
        f"- Findings recorded: **{len(findings)}**",
        "",
        "## Findings",
        "",
    ]
    for i, f in enumerate(findings, 1):
        lines.append(f"### {i}. [{f.get('severity', 'info').upper()}] {f.get('title')}")
        if f.get("detail"):
            lines.append(f"\n{f['detail']}\n")
        if f.get("recommendation"):
            lines.append(f"**Recommendation:** {f['recommendation']}\n")

    lines.extend(["## MCP tool notes", ""])
    for tool in READ_TOOLS:
        name = tool[0]
        res = tool_results.get(name)
        if isinstance(res, dict) and res.get("_error"):
            lines.append(f"- `{name}`: error")
        elif isinstance(res, dict) and res.get("_skipped"):
            lines.append(f"- `{name}`: skipped (not in tools/list)")
        else:
            lines.append(f"- `{name}`: ok")

    lines.append("\n---\n*Generated by ghl-audit-readonly.py*\n")
    path.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(["chown", "-R", "1000:1000", str(folder)], check=False)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only GHL audit")
    parser.add_argument("--slug", default="ghl", help="Account slug from ghl-accounts.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    account = ghl.account_by_slug(args.slug)
    if not account:
        raise SystemExit(f"Unknown slug: {args.slug}")

    env = load_env()
    pit = env.get(account["env_pit"], "").strip()
    location_id = env.get(account["env_location"], "").strip()
    if not pit or not location_id:
        raise SystemExit(f"Set {account['env_pit']} and {account['env_location']} in .env")

    print(f"=== GHL read-only audit: {account['display_name']} ===\n")

    if not args.dry_run:
        ensure_audit_tables()
        password = sync_db_password(account, env)
    else:
        password = env.get(account["env_db_password"], "")

    print("Fetching MCP tools/list...")
    listed = mcp_gateway("tools/list", pit=pit, location_id=location_id)
    available = set(tool_names_from_list(listed))
    print(f"  {len(available)} tools available")

    tool_results: dict[str, Any] = {}
    tool_calls = 0
    for name, arguments in READ_TOOLS:
        print(f"  call {name}...")
        tname, data = call_read_tool(name, arguments, pit, location_id, available)
        tool_results[tname] = data
        if not (isinstance(data, dict) and (data.get("_skipped") or data.get("_error"))):
            tool_calls += 1

    findings = analyze(account, tool_results, sorted(available))
    obsidian_rel = f"GHL/{account['obsidian_folder']}/Audits/{datetime.now(TZ).strftime('%Y-%m-%d')}-automation-review.md"
    run_id = insert_audit(
        account,
        password,
        location_id,
        findings,
        tool_calls,
        sorted(available),
        obsidian_rel,
        args.dry_run,
    )
    obs_path = write_obsidian(account, findings, tool_results, sorted(available), run_id)

    print(f"\nFindings: {len(findings)}")
    print(f"Obsidian: {obs_path}")
    if run_id:
        print(f"Postgres: {account['schema_prefix']}.audit_runs id={run_id}")
    print("Done (read-only — no CRM writes).")


if __name__ == "__main__":
    main()
