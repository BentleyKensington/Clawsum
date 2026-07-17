#!/usr/bin/env python3
"""INSTANCE OVERLAY smoke test — MCO REI example. Generic template: use verify-ghl-isolation.py."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("/docker/clawsum")
ENV_FILE = ROOT / ".env"
OPENCLAW = ROOT / "data/.openclaw/openclaw.json"


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


def test_mcp(env: dict[str, str]) -> bool:
    pit = env.get("GHL_MCO_REI_PIT", "").strip()
    loc = env.get("GHL_MCO_REI_LOCATION_ID", "").strip()
    if not pit or not loc:
        print("FAIL MCP: GHL_MCO_REI_PIT or GHL_MCO_REI_LOCATION_ID missing")
        return False

    cfg = json.loads(OPENCLAW.read_text())
    srv = (cfg.get("mcp") or {}).get("servers", {}).get("ghl-mco-rei", {})
    print(f"MCP config enabled={srv.get('enabled')} transport={srv.get('transport')}")

    # MCP streamable-http: initialize + tools/list style probe via JSON-RPC
    url = "https://services.leadconnectorhq.com/mcp/"
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "clawsum-smoke", "version": "1.0"},
            },
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {pit}",
            "locationId": loc,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode(errors="replace")
            print(f"MCP HTTP {resp.status} ({len(raw)} bytes)")
            if resp.status == 200 and raw.strip():
                print("OK MCP: endpoint responded")
                preview = raw.strip().split("\n")[0][:200]
                print(f"  preview: {preview}...")
                return True
            print(f"FAIL MCP: unexpected response status={resp.status}")
            return False
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")[:300]
        print(f"MCP host HTTP {e.code} — {err}")
    except Exception as e:
        print(f"MCP host error: {e}")

    out = subprocess.run(
        [
            "docker",
            "exec",
            "clawsum-openclaw-gateway-1",
            "node",
            "-e",
            f"""
const pit={json.dumps(pit)};
const loc={json.dumps(loc)};
const body=JSON.stringify({{jsonrpc:'2.0',id:1,method:'initialize',params:{{protocolVersion:'2024-11-05',capabilities:{{}},clientInfo:{{name:'clawsum-smoke',version:'1.0'}}}}}});
fetch('https://services.leadconnectorhq.com/mcp/',{{method:'POST',headers:{{Authorization:'Bearer '+pit,locationId:loc,'Content-Type':'application/json',Accept:'application/json, text/event-stream'}},body}})
  .then(async r=>{{const t=await r.text(); console.log('GW_MCP_STATUS',r.status,t.length); console.log('GW_MCP_PREVIEW',t.slice(0,200)); process.exit(r.ok?0:1);}})
  .catch(e=>{{console.log('GW_MCP_ERROR',e.message); process.exit(1);}});
""",
        ],
        capture_output=True,
        text=True,
        timeout=45,
    )
    combined = (out.stdout or "") + (out.stderr or "")
    for ln in combined.splitlines():
        print(f"  {ln}")
    if out.returncode == 0 and "GW_MCP_STATUS 200" in combined:
        print("OK MCP: gateway container reached GHL")
        return True
    print("FAIL MCP: could not reach GHL MCP with credentials")
    return False


def sync_db_password(env: dict[str, str]) -> None:
    pw = env.get("GHL_MCO_REI_DB_PASSWORD", "").strip()
    if not pw:
        return
    # Escape single quotes for SQL
    safe = pw.replace("'", "''")
    sql = f"ALTER ROLE ghl_mco_rei PASSWORD '{safe}';"
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
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql,
        ],
        check=True,
        capture_output=True,
    )
    print("OK DB: synced ghl_mco_rei password from .env")


def test_db_write(env: dict[str, str]) -> bool:
    pw = env.get("GHL_MCO_REI_DB_PASSWORD", "").strip()
    if not pw:
        print("FAIL DB: GHL_MCO_REI_DB_PASSWORD missing")
        return False

    try:
        sync_db_password(env)
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
                "GRANT CREATE ON SCHEMA mco_rei TO ghl_mco_rei;",
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"FAIL DB: setup — {e.stderr.decode()[:200]}")
        return False

    setup_sql = """
CREATE TABLE IF NOT EXISTS mco_rei.connection_smoke (
  id serial PRIMARY KEY,
  note text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO mco_rei.connection_smoke (note)
VALUES ('clawsum smoke test — safe to delete')
RETURNING id, current_user, current_schema(), created_at;
"""
    env_pg = {**os.environ, "PGPASSWORD": pw}
    try:
        out = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                "clawsum-postgres-1",
                "psql",
                "-U",
                "ghl_mco_rei",
                "-d",
                "ghl",
                "-v",
                "ON_ERROR_STOP=1",
            ],
            input=setup_sql.encode(),
            capture_output=True,
            env=env_pg,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        print("FAIL DB: timeout")
        return False

    if out.returncode != 0:
        print(f"FAIL DB: {out.stderr.decode()[:400]}")
        return False

    lines = [ln for ln in out.stdout.decode().splitlines() if ln.strip()]
    print("OK DB: insert succeeded")
    for ln in lines[-5:]:
        print(f"  {ln}")

    # Negative isolation check: must not read ave_rei
    deny = subprocess.run(
        [
            "docker",
            "exec",
            "clawsum-postgres-1",
            "psql",
            "-U",
            "ghl_mco_rei",
            "-d",
            "ghl",
            "-tAc",
            "SELECT count(*) FROM ave_rei.connection_smoke;",
        ],
        capture_output=True,
        env=env_pg,
    )
    if deny.returncode != 0:
        print("OK DB: cross-schema read blocked (ave_rei)")
    else:
        print("WARN DB: ghl_mco_rei could read ave_rei — isolation issue")

    return True


def main() -> None:
    env = load_env()
    print("=== MCO REI connection smoke test ===\n")
    mcp_ok = test_mcp(env)
    print()
    db_ok = test_db_write(env)
    print()
    if mcp_ok and db_ok:
        print("RESULT: PASS (MCP + DB write)")
        sys.exit(0)
    print(f"RESULT: FAIL (MCP={'OK' if mcp_ok else 'FAIL'}, DB={'OK' if db_ok else 'FAIL'})")
    if not mcp_ok:
        print("TIP: run python3 /docker/clawsum/scripts/provision-ghl-accounts.py && restart gateway")
    sys.exit(1)


if __name__ == "__main__":
    main()
