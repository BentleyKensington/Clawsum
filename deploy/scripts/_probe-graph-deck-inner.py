#!/usr/bin/env python3
import json
import sys

sys.path.insert(0, "/paperclip/.hermes/plugins/clawsum-cockpit/dashboard")
import plugin_api as api

resp = api.graphify(limit=64, q="", mode="map", cluster="")
body = json.loads(resp.body.decode())
print(
    json.dumps(
        {
            "ok": body.get("ok"),
            "nodes": len(body.get("nodes") or []),
            "edges": len(body.get("edges") or []),
            "facts": body.get("total_facts"),
            "clusters": [c.get("label") for c in (body.get("clusters") or [])],
            "sample": [n.get("label") for n in (body.get("nodes") or [])[:16]],
            "kinds": sorted({n.get("kind") for n in (body.get("nodes") or [])}),
            "arcade_up": (body.get("arcade") or {}).get("up"),
            "arcade_note": (body.get("arcade") or {}).get("note"),
            "obsidian": len((body.get("obsidian") or {}).get("nodes") or []),
            "obsidian_note": (body.get("obsidian") or {}).get("note"),
            "kpis": [
                {"id": k.get("id"), "value": k.get("value"), "source": k.get("source")}
                for k in (body.get("kpis") or [])
            ],
            "error": body.get("error"),
            "hint": body.get("hint"),
        },
        indent=2,
    )
)
