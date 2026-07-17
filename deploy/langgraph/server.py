"""Self-hosted LangGraph runner — OSS graphs without LangSmith license."""

from __future__ import annotations

import importlib
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

GRAPHS: dict[str, str] = {
    "gmail_triage": "graphs.gmail_triage:graph",
    "research_brief": "graphs.research_brief:graph",
}

_compiled: dict[str, Any] = {}

app = FastAPI(title="Clawsum LangGraph", version="0.1.0")


def _load_graph(name: str) -> Any:
    if name not in GRAPHS:
        raise KeyError(name)
    if name not in _compiled:
        mod_path, fn_name = GRAPHS[name].rsplit(":", 1)
        mod = importlib.import_module(mod_path)
        _compiled[name] = getattr(mod, fn_name)()
    return _compiled[name]


@app.on_event("startup")
def warmup() -> None:
    for name in GRAPHS:
        _load_graph(name)


@app.get("/ok")
def ok() -> dict[str, bool]:
    return {"ok": True}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class RunRequest(BaseModel):
    assistant_id: str
    input: dict[str, Any] = Field(default_factory=dict)


@app.post("/runs/wait")
def run_wait(req: RunRequest) -> dict[str, Any]:
    try:
        graph = _load_graph(req.assistant_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown assistant: {req.assistant_id}") from None

    output = graph.invoke(req.input)
    return {"assistant_id": req.assistant_id, "status": "success", "output": output}
