#!/usr/bin/env python3
import json
import urllib.request

url = "http://127.0.0.1:9119/api/plugins/clawsum-cockpit/graphify?mode=map&limit=64"
with urllib.request.urlopen(url, timeout=20) as resp:
    d = json.loads(resp.read().decode())
print(
    json.dumps(
        {
            "ok": d.get("ok"),
            "nodes": len(d.get("nodes") or []),
            "edges": len(d.get("edges") or []),
            "facts": d.get("total_facts"),
            "clusters": [c.get("label") for c in (d.get("clusters") or [])],
            "kinds": sorted({n.get("kind") for n in (d.get("nodes") or [])}),
            "arcade_up": (d.get("arcade") or {}).get("up"),
            "arcade_note": (d.get("arcade") or {}).get("note"),
            "obsidian": len((d.get("obsidian") or {}).get("nodes") or []),
            "obsidian_note": (d.get("obsidian") or {}).get("note"),
            "kpis": [
                {"id": k.get("id"), "value": k.get("value"), "source": k.get("source")}
                for k in (d.get("kpis") or [])
            ],
            "grafana": d.get("grafana"),
            "error": d.get("error"),
            "hint": d.get("hint"),
        },
        indent=2,
    )
)
