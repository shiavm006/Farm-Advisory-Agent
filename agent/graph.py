"""
LangGraph Workflow
Wires all nodes into a sequential graph:
  parse_input → predict_yield → assess_risk → retrieve_docs → generate_advice → END
"""

from typing import Optional
from langgraph.graph import StateGraph, END
from agent.state import FarmState
from agent.nodes import (
    parse_input,
    predict_yield,
    assess_risk,
    retrieve_docs,
    generate_advice,
    chat_turn,
)


def build_graph():
    """Build and compile the farm advisory LangGraph."""

    graph = StateGraph(FarmState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("parse_input", parse_input)
    graph.add_node("predict_yield", predict_yield)
    graph.add_node("assess_risk", assess_risk)
    graph.add_node("retrieve_docs", retrieve_docs)
    graph.add_node("generate_advice", generate_advice)

    # ── Entry point ───────────────────────────────────────────────────────────
    graph.set_entry_point("parse_input")

    # ── Edges (sequential pipeline) ───────────────────────────────────────────
    graph.add_edge("parse_input", "predict_yield")
    graph.add_edge("predict_yield", "assess_risk")
    graph.add_edge("assess_risk", "retrieve_docs")
    graph.add_edge("retrieve_docs", "generate_advice")
    graph.add_edge("generate_advice", END)

    return graph.compile()


def build_chat_graph():
    """Build and compile the chat-turn LangGraph (conversational mode).

    Flow: chat_turn → END
    Each call handles exactly one conversational turn using retrieval +
    full chat history. ML yield prediction is kept separate (run_agent) so
    conversation stays fast.
    """
    graph = StateGraph(FarmState)
    graph.add_node("chat_turn", chat_turn)
    graph.set_entry_point("chat_turn")
    graph.add_edge("chat_turn", END)
    return graph.compile()


# Singletons — each compiled once and reused
_graph = None
_chat_graph = None


def get_graph():
    """Return singleton compiled advisory graph."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def get_chat_graph():
    """Return singleton compiled chat graph."""
    global _chat_graph
    if _chat_graph is None:
        _chat_graph = build_chat_graph()
    return _chat_graph


def run_agent(
    crop: str,
    area: str,
    year: int,
    rainfall: float,
    temperature: float,
    pesticides: float,
    user_query: str = "",
) -> FarmState:
    """
    Main entry point to run the full advisory agent.

    Returns the final FarmState with all fields populated.
    """
    graph = get_graph()

    initial_state: FarmState = {
        "crop": crop,
        "area": area,
        "year": year,
        "rainfall": rainfall,
        "temperature": temperature,
        "pesticides": pesticides,
        "user_query": user_query,
        "predicted_yield_hg": None,
        "predicted_yield_tha": None,
        "yield_risk": None,
        "yield_band": None,
        "benchmark_avg": None,
        "retrieved_docs": None,
        "source_files": None,
        "field_summary": None,
        "recommendations": None,
        "sources": None,
        "disclaimer": None,
        "error": None,
    }

    result = graph.invoke(initial_state)
    return result


def run_chat(
    messages: list,
    farm_ctx: Optional[dict] = None,
    uploaded_docs_text: str = "",
) -> FarmState:
    """
    Run one conversational turn of the farm advisory agent.

    Args:
      messages: full chat history including the new user message as the
                last item. Each item is {"role": "user"|"assistant", "content": str}.
      farm_ctx: optional dict with farm context
                (keys: crop, area, year, rainfall, temperature, pesticides,
                 predicted_yield_tha, yield_band, yield_risk, benchmark_avg).
      uploaded_docs_text: raw text from user-uploaded reference documents.

    Returns:
      The updated FarmState. Use result["assistant_reply"] for the newest reply,
      result["messages"] for the full updated history, and result["source_files"]
      for retrieved sources.
    """
    farm_ctx = farm_ctx or {}

    initial_state: FarmState = {
        "crop": farm_ctx.get("crop", ""),
        "area": farm_ctx.get("area", ""),
        "year": int(farm_ctx.get("year", 2024) or 2024),
        "rainfall": float(farm_ctx.get("rainfall", 0.0) or 0.0),
        "temperature": float(farm_ctx.get("temperature", 0.0) or 0.0),
        "pesticides": float(farm_ctx.get("pesticides", 0.0) or 0.0),
        "user_query": messages[-1]["content"] if messages else "",
        "predicted_yield_hg": farm_ctx.get("predicted_yield_hg"),
        "predicted_yield_tha": farm_ctx.get("predicted_yield_tha"),
        "yield_risk": farm_ctx.get("yield_risk"),
        "yield_band": farm_ctx.get("yield_band"),
        "benchmark_avg": farm_ctx.get("benchmark_avg"),
        "retrieved_docs": None,
        "source_files": None,
        "field_summary": None,
        "recommendations": None,
        "sources": None,
        "disclaimer": None,
        "messages": list(messages),
        "assistant_reply": None,
        "uploaded_docs_text": uploaded_docs_text or "",
        "error": None,
    }

    graph = get_chat_graph()
    return graph.invoke(initial_state)
