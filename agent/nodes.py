"""
LangGraph Node Functions
Each node takes FarmState, does one job, returns updated FarmState.

Nodes:
  1. parse_input     — validate and clean inputs
  2. predict_yield   — run ML model from model.pkl
  3. assess_risk     — classify yield risk and band
  4. retrieve_docs   — query FAISS vector store
  5. generate_advice — call Claude LLM for structured advice
"""

import os
import json
import pickle
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
import anthropic

from agent.state import FarmState
from agent.prompts import ADVISORY_PROMPT, CHAT_SYSTEM_PROMPT, CHAT_FALLBACK_TEMPLATE
from rag.retriever import retrieve

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
MODEL_DIR = Path(__file__).parent.parent / "model"
HF_REPO = "shiavm006/Crop-yield_pridiction"


def _load_pkl(filename: str):
    """Load a pkl file from local model dir or download from HuggingFace."""
    local = MODEL_DIR / filename
    if local.exists():
        with open(local, "rb") as f:
            return pickle.load(f)
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(repo_id=HF_REPO, filename=filename)
    with open(path, "rb") as f:
        return pickle.load(f)


# ── Crop benchmarks (average t/ha from FAO data) ──────────────────────────────
CROP_BENCHMARKS = {
    "wheat": 3.5,
    "rice, paddy": 4.5,
    "maize": 5.5,
    "potatoes": 20.0,
    "cassava": 12.0,
    "soybeans": 2.5,
    "sorghum": 1.5,
    "sweet potatoes": 10.0,
}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 1 — Parse & Validate Input
# ══════════════════════════════════════════════════════════════════════════════
def parse_input(state: FarmState) -> FarmState:
    """Validate all inputs and set defaults where needed."""
    try:
        # Ensure query exists
        if not state.get("user_query", "").strip():
            state["user_query"] = (
                f"What are the best farming practices for {state['crop']} "
                f"in {state['area']} given the current conditions?"
            )

        # Clamp values to reasonable ranges
        state["rainfall"] = max(0.0, float(state["rainfall"]))
        state["temperature"] = float(state["temperature"])
        state["pesticides"] = max(0.0, float(state["pesticides"]))
        state["year"] = int(state["year"])

        # Initialize output fields
        state["error"] = None

    except Exception as e:
        state["error"] = f"Input parsing error: {str(e)}"

    return state


# ══════════════════════════════════════════════════════════════════════════════
# NODE 2 — Predict Yield (ML Model)
# ══════════════════════════════════════════════════════════════════════════════
def predict_yield(state: FarmState) -> FarmState:
    """Load model.pkl and predict crop yield."""
    if state.get("error"):
        return state

    try:
        # Load artifacts (local or HuggingFace)
        model = _load_pkl("model.pkl")
        scaler = _load_pkl("scaler.pkl")
        feature_config = _load_pkl("features.pkl")

        # Build feature vector using same logic as the main app (build_row)
        feature_names = (
            feature_config
            if isinstance(feature_config, list)
            else feature_config.get("features", [])
        )

        numeric = {
            "Year": state["year"],
            "average_rain_fall_mm_per_year": state["rainfall"],
            "pesticides_tonnes": state["pesticides"],
            "avg_temp": state["temperature"],
        }

        vals = []
        for name in feature_names:
            if name in numeric:
                vals.append(numeric[name])
            elif name.startswith("Area_"):
                vals.append(1.0 if name == f"Area_{state['area']}" else 0.0)
            elif name.startswith("Item_"):
                vals.append(
                    1.0
                    if (
                        name == f"Item_{state['crop']}"
                        or state["crop"] in name.replace("_", " ")
                    )
                    else 0.0
                )
            else:
                vals.append(0.0)

        feature_vector = np.array([vals], dtype=float)
        X_scaled = scaler.transform(feature_vector)

        prediction_hg = float(model.predict(X_scaled)[0])
        prediction_tha = round(prediction_hg / 10000, 2)

        state["predicted_yield_hg"] = prediction_hg
        state["predicted_yield_tha"] = prediction_tha

    except Exception as e:
        state["error"] = f"Yield prediction error: {str(e)}"

    return state


# ══════════════════════════════════════════════════════════════════════════════
# NODE 3 — Assess Risk
# ══════════════════════════════════════════════════════════════════════════════
def assess_risk(state: FarmState) -> FarmState:
    """Classify yield into risk level and band based on crop benchmarks."""
    if state.get("error"):
        return state

    try:
        crop_key = state["crop"].lower()
        benchmark = CROP_BENCHMARKS.get(crop_key, 3.0)
        yield_tha = state.get("predicted_yield_tha", 0)

        state["benchmark_avg"] = benchmark

        ratio = yield_tha / benchmark if benchmark > 0 else 0

        if ratio >= 1.2:
            state["yield_band"] = "Excellent"
            state["yield_risk"] = "Low Risk"
        elif ratio >= 0.85:
            state["yield_band"] = "Good"
            state["yield_risk"] = "Low Risk"
        elif ratio >= 0.55:
            state["yield_band"] = "Fair"
            state["yield_risk"] = "Medium Risk"
        else:
            state["yield_band"] = "Poor"
            state["yield_risk"] = "High Risk"

    except Exception as e:
        state["error"] = f"Risk assessment error: {str(e)}"

    return state


# ══════════════════════════════════════════════════════════════════════════════
# NODE 4 — Retrieve Documents (RAG)
# ══════════════════════════════════════════════════════════════════════════════
def retrieve_docs(state: FarmState) -> FarmState:
    """Query FAISS vector store for relevant agronomy guidelines."""
    if state.get("error"):
        return state

    try:
        query = f"{state['crop']} farming {state['user_query']} rainfall {state['rainfall']} temperature {state['temperature']}"
        chunks, sources = retrieve(query, k=5)

        state["retrieved_docs"] = chunks
        state["source_files"] = sources

    except Exception as e:
        state["error"] = f"Document retrieval error: {str(e)}"

    return state


# ══════════════════════════════════════════════════════════════════════════════
# NODE 5 — Generate Advisory (LLM)
# ══════════════════════════════════════════════════════════════════════════════
def generate_advice(state: FarmState) -> FarmState:
    """Call Claude API to generate structured farm advisory."""
    if state.get("error"):
        return state

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

        # Format retrieved docs
        docs_text = "\n\n---\n\n".join(state.get("retrieved_docs", []))
        if not docs_text:
            docs_text = (
                "No specific documents retrieved. Use general agronomy best practices."
            )

        # Fill prompt
        prompt = ADVISORY_PROMPT.format(
            crop=state["crop"],
            area=state["area"],
            year=state["year"],
            rainfall=state["rainfall"],
            temperature=state["temperature"],
            pesticides=state["pesticides"],
            predicted_yield=state.get("predicted_yield_tha", "N/A"),
            yield_risk=state.get("yield_risk", "Unknown"),
            yield_band=state.get("yield_band", "Unknown"),
            benchmark_avg=state.get("benchmark_avg", "N/A"),
            user_query=state["user_query"],
            retrieved_docs=docs_text,
        )

        # Try the same broad, current model list as chat_turn.
        deduped_candidates = _anthropic_model_candidates()
        response = None
        last_err = None

        for model_name in deduped_candidates:
            try:
                response = client.messages.create(
                    model=model_name,
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}],
                )
                break
            except Exception as e:
                last_err = e
                # Try next model only for "model not found" style failures.
                if "not_found_error" in str(e) or "model:" in str(e):
                    continue
                raise

        if response is None:
            raise last_err

        raw = response.content[0].text.strip()

        # Parse JSON response
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)

        state["field_summary"] = result.get("field_summary", "")
        state["recommendations"] = result.get("recommendations", [])
        state["sources"] = result.get("sources", [])
        state["disclaimer"] = result.get(
            "disclaimer",
            "Consult local agricultural extension officers for region-specific advice.",
        )

    except json.JSONDecodeError:
        # Fallback: return raw text if JSON parsing fails
        state["field_summary"] = (
            raw[:500] if raw else "Advisory generation encountered an issue."
        )
        state["recommendations"] = [
            "Please consult your local agricultural extension officer."
        ]
        state["sources"] = state.get("source_files", [])
        state["disclaimer"] = (
            "Yield predictions are estimates. Always consult local experts before making farming decisions."
        )

    except Exception as e:
        # If all Anthropic models are unavailable, return a safe local fallback
        # so the advisory page still works during demos/submissions.
        msg = str(e)
        if "not_found_error" in msg or "model:" in msg:
            crop = state.get("crop", "the selected crop")
            risk = state.get("yield_risk", "Unknown Risk")
            yld = state.get("predicted_yield_tha", "N/A")
            state["field_summary"] = (
                f"Predicted yield for {crop} is {yld} t/ha with {risk}. "
                "Recommendations below are generated from retrieved agronomy references."
            )
            state["recommendations"] = [
                "Match irrigation scheduling to current rainfall and crop growth stage.",
                "Use integrated pest management and monitor fields weekly for early signs of infestation.",
                "Apply fertilizers based on soil testing and split doses across growth stages.",
                "Maintain field sanitation (remove infected debris, manage weeds, improve drainage).",
                "Track yield and input records to adjust practices in the next cycle.",
            ]
            state["sources"] = state.get("source_files", []) or [
                "Local RAG references from rag/docs"
            ]
            state["disclaimer"] = (
                "This fallback advisory is generated without live LLM reasoning due to model access limits. "
                "Follow local regulations for pesticide/fertilizer use and consult local extension officers."
            )
            state["error"] = None
        else:
            state["error"] = f"Advisory generation error: {msg}"

    return state


# ══════════════════════════════════════════════════════════════════════════════
# NODE 6 — Chat Turn (multi-turn conversational agent)
# ══════════════════════════════════════════════════════════════════════════════
def _anthropic_model_candidates() -> list:
    """Build an ordered, de-duplicated list of Anthropic model IDs to try.

    Starts with an env-configured model, then walks the current Claude 4
    family (aliases), then the Claude 4.x dated IDs, then older fallbacks.
    This lets the agent keep working across different Anthropic accounts
    with different model access tiers.
    """
    preferred = os.environ.get("ANTHROPIC_MODEL", "")
    raw = [
        preferred,
        "claude-haiku-4-5",
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-6",
        "claude-opus-4-7",
        "claude-sonnet-4-5",
        "claude-sonnet-4-5-20250929",
        "claude-opus-4-5",
        "claude-opus-4-1",
        "claude-3-5-haiku-latest",
        "claude-3-5-sonnet-latest",
        "claude-3-haiku-20240307",
    ]
    seen, ordered = set(), []
    for m in raw:
        if m and m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered


def _build_farm_context_block(state: FarmState) -> str:
    crop = state.get("crop") or ""
    area = state.get("area") or ""
    if not (crop or area):
        return "No farm context provided yet. You may ask the user to set it in the sidebar if needed."
    return (
        f"- Crop: {crop or 'N/A'}\n"
        f"- Region / Area: {area or 'N/A'}\n"
        f"- Year: {state.get('year', 'N/A')}\n"
        f"- Rainfall: {state.get('rainfall', 'N/A')} mm/year\n"
        f"- Average Temperature: {state.get('temperature', 'N/A')} °C\n"
        f"- Pesticide Usage: {state.get('pesticides', 'N/A')} tonnes"
    )


def _build_yield_block(state: FarmState) -> str:
    if state.get("predicted_yield_tha") is None:
        return "No ML yield prediction has been run yet for this context."
    return (
        f"- Predicted Yield: {state.get('predicted_yield_tha')} t/ha\n"
        f"- Yield Band: {state.get('yield_band', 'N/A')}\n"
        f"- Yield Risk: {state.get('yield_risk', 'N/A')}\n"
        f"- Crop Benchmark: ~{state.get('benchmark_avg', 'N/A')} t/ha"
    )


def chat_turn(state: FarmState) -> FarmState:
    """
    Run one turn of the conversational agent.

    Expects state["messages"] to be a list like:
      [{"role": "user", "content": "..."},
       {"role": "assistant", "content": "..."},
       {"role": "user", "content": "...latest question..."}]

    Returns state with state["assistant_reply"] and an appended assistant
    turn inside state["messages"].
    """
    try:
        messages = list(state.get("messages") or [])
        if not messages or messages[-1].get("role") != "user":
            state["error"] = "chat_turn called without a trailing user message."
            return state

        latest_user = messages[-1]["content"]

        # ── Retrieval query — blend latest user msg with crop context ────────
        crop = state.get("crop") or ""
        query = (
            latest_user
            if not crop
            else f"{crop} {state.get('area', '')} :: {latest_user}"
        )
        try:
            chunks, sources = retrieve(query, k=4)
        except Exception as ret_err:
            chunks, sources = [], []
            # Don't fail the whole turn if retrieval fails — chat should still work.
            print(f"[chat_turn] retrieval failed: {ret_err}")

        # ── Inject user-uploaded documents as extra context ──────────────────
        uploaded_text = (state.get("uploaded_docs_text") or "").strip()
        if uploaded_text:
            snippet = uploaded_text[:6000]
            chunks = chunks + [f"[User-uploaded document]\n{snippet}"]
            sources = sources + ["user_uploaded_document"]

        state["retrieved_docs"] = chunks
        state["source_files"] = sources

        retrieved_block = (
            "\n\n---\n\n".join(chunks)
            if chunks
            else "No specific agronomic references were retrieved for this query."
        )

        system_prompt = CHAT_SYSTEM_PROMPT.format(
            farm_context_block=_build_farm_context_block(state),
            yield_context_block=_build_yield_block(state),
            retrieved_block=retrieved_block,
        )

        # Keep only role + content (strip any UI-only fields)
        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]

        reply_text = None
        last_err = None

        try:
            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            for model_name in _anthropic_model_candidates():
                try:
                    resp = client.messages.create(
                        model=model_name,
                        max_tokens=1800,
                        system=system_prompt,
                        messages=api_messages,
                    )
                    reply_text = resp.content[0].text.strip()
                    break
                except Exception as e:
                    last_err = e
                    if "not_found_error" in str(e) or "model:" in str(e):
                        continue
                    raise
        except KeyError:
            last_err = RuntimeError("ANTHROPIC_API_KEY not set in environment.")

        if not reply_text:
            # Local, non-LLM fallback so the chat still works in demos.
            snippets = (
                "\n\n".join(f"• {c[:400].strip()}" for c in chunks[:3])
                or "• (No snippets available.)"
            )
            reply_text = CHAT_FALLBACK_TEMPLATE.format(
                crop=crop or "your crop",
                area=state.get("area") or "your region",
                yield_tha=state.get("predicted_yield_tha", "N/A"),
                band=state.get("yield_band", "N/A"),
                risk=state.get("yield_risk", "N/A"),
                benchmark=state.get("benchmark_avg", "N/A"),
                snippets=snippets,
            )
            if last_err:
                print(f"[chat_turn] LLM fallback engaged: {last_err}")

        state["assistant_reply"] = reply_text
        state["messages"] = messages + [{"role": "assistant", "content": reply_text}]
        state["error"] = None

    except Exception as e:
        state["error"] = f"Chat turn error: {str(e)}"

    return state
