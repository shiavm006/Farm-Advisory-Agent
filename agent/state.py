from typing import TypedDict, Optional, List, Dict


class FarmState(TypedDict, total=False):
    """
    Shared state passed between every node in the LangGraph agent.
    Each node reads from and writes to this dictionary.
    """

    # ── User Inputs ──────────────────────────────────────────────────────────
    crop: str  # e.g. "Wheat", "Rice, paddy"
    area: str  # e.g. "India", "Brazil"
    year: int  # e.g. 2024
    rainfall: float  # mm per year
    temperature: float  # avg °C
    pesticides: float  # tonnes
    user_query: str  # free-text advisory question from user

    # ── ML Prediction (filled by predict_yield node) ─────────────────────────
    predicted_yield_hg: Optional[float]  # raw model output in hg/ha
    predicted_yield_tha: Optional[float]  # converted to t/ha

    # ── Risk Assessment (filled by assess_risk node) ──────────────────────────
    yield_risk: Optional[str]  # "Low Risk" / "Medium Risk" / "High Risk"
    yield_band: Optional[str]  # "Poor" / "Fair" / "Good" / "Excellent"
    benchmark_avg: Optional[float]  # typical yield for this crop (t/ha)

    # ── RAG (filled by retrieve_docs node) ────────────────────────────────────
    retrieved_docs: Optional[List[str]]  # list of relevant text chunks
    source_files: Optional[List[str]]  # which doc files were retrieved

    # ── LLM Output (filled by generate_advice node) ───────────────────────────
    field_summary: Optional[str]  # Crop & field condition summary
    recommendations: Optional[List[str]]  # List of actionable advice
    sources: Optional[List[str]]  # Agronomic reference snippets
    disclaimer: Optional[str]  # Safety / agricultural disclaimer

    # ── Chat Mode (multi-turn conversation) ──────────────────────────────────
    messages: List[Dict[str, str]]  # [{"role": "user"|"assistant", "content": "..."}]
    assistant_reply: Optional[str]  # latest assistant message text
    uploaded_docs_text: Optional[str]  # raw text of user-uploaded reference docs

    # ── Error Handling ────────────────────────────────────────────────────────
    error: Optional[str]  # Set if any node fails
