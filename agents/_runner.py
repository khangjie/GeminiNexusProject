"""
ADK runner utility + ADK import guard.

All agent pipeline files import `ADK_AVAILABLE`, `adk_agent_class`,
`run_adk_pipeline`, and the ADK type classes from here so they only
need a single try/except instead of one in every file.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── ADK availability guard ────────────────────────────────────────────────────
ADK_AVAILABLE = False
Agent = None
SequentialAgent = None
ParallelAgent = None
FunctionTool = None
Runner = None
InMemorySessionService = None
genai_types = None

try:
    from google.adk.agents import Agent, SequentialAgent, ParallelAgent  # type: ignore
    from google.adk.tools import FunctionTool  # type: ignore
    from google.adk.runners import Runner  # type: ignore
    from google.adk.sessions import InMemorySessionService  # type: ignore
    from google.genai import types as genai_types  # type: ignore
    ADK_AVAILABLE = True
    logger.info("Google ADK loaded successfully.")
except ImportError:
    logger.warning(
        "google-adk not importable — multi-agent pipelines will fall back to "
        "direct Gemini API prompts. Install with: pip install google-adk"
    )


# ── Gemini direct-client fallback ─────────────────────────────────────────────

def _get_gemini_model(model_name: str):
    """Return a google.generativeai.GenerativeModel or None."""
    try:
        import google.generativeai as genai
        from app.core.config import get_settings
        s = get_settings()
        if s.GOOGLE_API_KEY:
            genai.configure(api_key=s.GOOGLE_API_KEY)
        return genai.GenerativeModel(model_name)
    except Exception:
        return None


def _safe_json(text: str) -> dict:
    """Extract first JSON object from LLM response text."""
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {}


def _safe_json_array(text: str) -> list:
    """Extract first JSON array from LLM response text."""
    try:
        start = text.index("[")
        end = text.rindex("]") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return []


# ── ADK async runner ──────────────────────────────────────────────────────────

async def run_adk_pipeline(agent: Any, initial_prompt: str) -> str:
    """
    Execute an ADK agent (Agent, SequentialAgent, or ParallelAgent) with
    `initial_prompt` as the first user message.  Returns the final text
    response from the agent.
    """
    if not ADK_AVAILABLE or agent is None:
        raise RuntimeError("ADK not available")

    from app.core.config import get_settings
    s = get_settings()

    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="nexus_expense_hub",
        session_service=session_service,
    )
    session = session_service.create_session(
        app_name="nexus_expense_hub",
        user_id="system",
    )

    logger.info("ADK runner started for app=nexus_expense_hub session_id=%s", session.id)

    final_text = ""
    try:
        async for event in runner.run_async(
            user_id="system",
            session_id=session.id,
            new_message=genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=initial_prompt)],
            ),
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_text = event.content.parts[-1].text or final_text
    except Exception as exc:
        logger.error("ADK pipeline error: %s", exc)
        raise

    logger.info("ADK runner finished for session_id=%s has_final_response=%s", session.id, bool(final_text))

    return final_text
