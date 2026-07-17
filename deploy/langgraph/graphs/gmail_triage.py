"""Minimal gmail_triage graph stub — extend for production triage."""

from typing import TypedDict


class State(TypedDict, total=False):
    email_id: str
    status: str
    notes: str


def triage(state: State) -> State:
    return {**state, "status": "pending", "notes": "stub — wire to gmail-triage.py"}


def graph():
    from langgraph.graph import END, StateGraph

    g = StateGraph(State)
    g.add_node("triage", triage)
    g.set_entry_point("triage")
    g.add_edge("triage", END)
    return g.compile()
