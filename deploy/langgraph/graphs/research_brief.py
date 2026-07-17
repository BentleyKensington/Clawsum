"""Minimal research_brief graph stub."""

from typing import TypedDict


class State(TypedDict, total=False):
    topic: str
    brief: str


def summarize(state: State) -> State:
    topic = state.get("topic", "untitled")
    return {**state, "brief": f"stub brief for: {topic}"}


def graph():
    from langgraph.graph import END, StateGraph

    g = StateGraph(State)
    g.add_node("summarize", summarize)
    g.set_entry_point("summarize")
    g.add_edge("summarize", END)
    return g.compile()
