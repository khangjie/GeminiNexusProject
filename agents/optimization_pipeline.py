"""
Proposal Optimization Pipeline — ADK multi-agent implementation.

Replacement/Alternative Item Flow (matches ProjectStructure.litcoffee):

  Owner Selects Item From Proposal
          │
          ▼
  SequentialAgent: item_context_pipeline
          ├── context_builder_agent       (extract item context)
          └── query_optimizer_agent       (refine search keywords)
          │
          ▼
  ParallelAgent: market_search_pipeline
          ├── google_search_agent         (find online prices)
          ├── review_retrieval_agent      (get ratings & reviews)
          └── rag_history_agent           (search company purchase history)
          │
          ▼
  aggregation_agent                       (merge + rank results)
          │
          ▼
  recommendation_agent                    (generate final alternatives list)

Public API:
    run_proposal_optimization_pipeline(item, search_name, company_id) -> list[dict]
"""
from __future__ import annotations

import json
import logging
from urllib.parse import urlparse
from typing import Any
import httpx

from agents._runner import (
    ADK_AVAILABLE,
    Agent,
    ParallelAgent,
    SequentialAgent,
    _get_gemini_model,
    _safe_json_array,
    run_adk_pipeline,
)
from agents.tools import rag_history_tool, set_pipeline_context
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
MODEL = settings.GEMINI_MODEL


# ── Agent Definitions ─────────────────────────────────────────────────────────

def _build_agents():
    if not ADK_AVAILABLE:
        return None

    # 1. Context Builder — extract structured item context
    context_builder = Agent(
        name="context_builder_agent",
        model=MODEL,
        instruction="""You are the Item Context Builder Agent.

Your task is to extract a rich context object from the provided item information
to guide the subsequent price comparison search.

Respond with a JSON object:
{
  "item_name": "clean product name",
  "category": "product category (e.g. Electronics, Stationery, Food)",
  "current_price": number | null,
  "vendor": "current vendor name" | null,
  "key_attributes": ["list", "of", "important", "product", "attributes"],
  "search_intent": "brief description of what to look for"
}

Output ONLY the JSON object.
""",
        output_key="item_context",
    )

    # 2. Query Optimizer — refine search keywords for better results
    query_optimizer = Agent(
        name="search_query_optimizer_agent",
        model=MODEL,
        instruction="""You are the Search Query Optimizer Agent.

Based on the item context from the previous agent, generate optimized search
queries that will find the best price alternatives online.

Respond with a JSON object:
{
  "primary_query": "main search query for price comparison",
  "alternative_queries": ["query1", "query2"],
  "price_range_hint": "under $X" | null,
  "brand_flexibility": "any" | "same_brand" | "branded_only"
}

Output ONLY the JSON object.
""",
        output_key="search_queries",
    )

    # 3. Google Search Agent — online price comparison
    google_search = Agent(
        name="google_search_agent",
        model=MODEL,
        instruction="""You are the Google Search Agent for product price comparison.

Based on the item context and optimized search queries from earlier in this
      conversation, return ONLY real product listing results with clickable URLs.
      Never invent vendors, prices, or links.

Respond with a JSON array of product alternatives found online:
[
  {
    "vendor": "Store Name",
    "price": 00.00,
    "currency": "USD",
    "product_name": "exact product name",
          "product_url": "https://example.com/product",
    "source": "online"
  }
]

      Return up to 5 options. If no reliable results are available, return [].
      Output ONLY the JSON array.
""",
        output_key="online_results",
    )

    # 4. Review Retrieval Agent — ratings and review summaries
    review_retrieval = Agent(
        name="review_retrieval_agent",
        model=MODEL,
        instruction="""You are the Review Retrieval Agent.

Based on the product search results from earlier in this conversation,
retrieve ratings and review summaries for each alternative option.

Respond with a JSON array matching the online results, adding review data:
[
  {
    "vendor": "Store Name",
    "rating": 4.5,
    "review_count": 1200,
    "review_summary": "Concise 1-2 sentence summary of customer reviews",
    "pros": ["pro1", "pro2"],
    "cons": ["con1"]
  }
]

Output ONLY the JSON array.
""",
        output_key="review_results",
    )

    # 5. RAG History Agent — search company purchase history
    rag_history = Agent(
        name="rag_receipt_history_agent",
        model=MODEL,
        instruction="""You are the RAG Receipt History Agent.

Use the `search_company_purchase_history` tool to find similar items the
company has purchased before. This helps identify if there's a better
historical vendor to consider.

Based on the results, respond with a JSON array:
[
  {
    "vendor": "Historical Vendor",
    "price": 00.00,
    "date": "YYYY-MM-DD",
    "source": "company_history",
    "note": "brief note about this historical purchase"
  }
]

Output ONLY the JSON array.
""",
        tools=[rag_history_tool],
        output_key="history_results",
    )

    # 6. Aggregation Agent — merge and rank all results
    aggregation = Agent(
        name="alternative_aggregation_agent",
        model=MODEL,
        instruction="""You are the Alternative Aggregation Agent.

You have access to results from:
  - google_search_agent    → online prices
  - review_retrieval_agent → ratings and reviews
  - rag_history_agent      → company purchase history

Merge all sources, remove duplicates, and rank options by value.

Respond with a unified JSON array (best options first by value score):
[
  {
    "rank": 1,
    "vendor": "Store Name",
    "price": 00.00,
    "rating": 4.5,
    "review_summary": "...",
    "product_url": "https://example.com/product" | null,
    "source": "online" | "company_history",
    "value_score": 0.0-1.0,
    "highlight": "why this is a good choice"
  }
]

Output ONLY the JSON array.
""",
        output_key="aggregated_results",
    )

    # 7. Recommendation Agent — generate the final alternatives list
    recommendation = Agent(
        name="recommendation_agent",
        model=MODEL,
        instruction="""You are the Recommendation Agent — the final step in the
proposal optimization pipeline.

Based on the aggregated results from the previous agent, produce the final
recommendation list for the owner to choose from.

Respond with a JSON array of alternatives, sorted best-first:
[
  {
    "vendor": "Store Name",
    "price": 00.00,
    "rating": 4.5,
    "review_summary": "customer review highlights",
    "product_url": "https://example.com/product" | null,
    "source": "online" | "company_history",
    "savings": 00.00,
    "savings_pct": 0.0
  }
]

Include savings vs. the current item price where applicable.
For source="online", product_url is required and must be an absolute http/https URL.
If an option cannot provide a valid product_url, omit it.
Output ONLY the JSON array.
""",
        output_key="final_recommendations",
    )

    return {
        "context_builder": context_builder,
        "query_optimizer": query_optimizer,
        "google_search": google_search,
        "review_retrieval": review_retrieval,
        "rag_history": rag_history,
        "aggregation": aggregation,
        "recommendation": recommendation,
    }


def _build_pipeline(agents: dict):
    context_pipeline = SequentialAgent(
        name="item_context_pipeline",
        description="Builds item context and optimizes search queries.",
        sub_agents=[
            agents["context_builder"],
            agents["query_optimizer"],
        ],
    )

    market_search_pipeline = ParallelAgent(
        name="market_search_pipeline",
        description="Simultaneously searches online prices, reviews, and company purchase history.",
        sub_agents=[
            agents["google_search"],
            agents["review_retrieval"],
            agents["rag_history"],
        ],
    )

    return SequentialAgent(
        name="item_optimization_pipeline",
        description="Full proposal item optimization pipeline.",
        sub_agents=[
            context_pipeline,
            market_search_pipeline,
            agents["aggregation"],
            agents["recommendation"],
        ],
    )


# ── Public pipeline runner ────────────────────────────────────────────────────

async def run_proposal_optimization_pipeline(
    item: Any,
    search_name: str | None,
    company_id: str,
) -> list[dict]:
    """
    Find cheaper/better alternatives for a proposal receipt item.

    Falls back to direct Gemini prompt if ADK is unavailable.
    """
    set_pipeline_context(db=None, company_id=company_id)
    query = search_name or item.name

    initial_prompt = f"""Find alternative purchasing options for the following item:

Item Name:     {item.name}
Current Price: {item.price}
Search Name:   {query}
Company ID:    {company_id}

Please run the full optimization pipeline to find better/cheaper alternatives."""

    # ── Try ADK pipeline ──────────────────────────────────────────────────────
    if ADK_AVAILABLE:
        try:
            agents = _build_agents()
            pipeline = _build_pipeline(agents)
            final_text = await run_adk_pipeline(pipeline, initial_prompt)
            alternatives = _safe_json_array(final_text)
            if alternatives:
              normalized = _normalize_alternatives(alternatives, item.price)
              return await _filter_reachable_alternatives(normalized)
        except Exception as exc:
            logger.warning("ADK optimization pipeline failed (%s), using Gemini fallback.", exc)

    # ── Gemini direct fallback ────────────────────────────────────────────────
    return await _gemini_fallback_alternatives(item, query)


def _is_valid_http_url(value: Any) -> bool:
  if not isinstance(value, str) or not value.strip():
    return False
  parsed = urlparse(value.strip())
  return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_alternatives(raw: list, current_price: float | None) -> list[dict]:
  result = []
  for a in raw:
    price = float(a.get("price", 0) or 0)
    product_url = a.get("product_url")
    source = a.get("source", "online")

    # Require link-backed alternatives so owners can verify before replacing.
    if not _is_valid_http_url(product_url):
      continue

    savings = round((current_price or 0) - price, 2) if current_price else None
    result.append({
      "vendor": a.get("vendor", "Unknown"),
      "price": price,
      "rating": a.get("rating"),
      "review_summary": a.get("review_summary"),
      "product_url": product_url,
      "source": source,
      "savings": savings,
    })
  return result


async def _is_reachable_url(url: str) -> bool:
  timeout = httpx.Timeout(5.0, connect=3.0)
  headers = {"User-Agent": "ExpenseHub-AlternativeChecker/1.0"}

  try:
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
      head = await client.head(url)
      if head.status_code < 400:
        return True

      # Some stores block HEAD; retry with GET.
      get = await client.get(url)
      return get.status_code < 400
  except Exception:
    return False


async def _filter_reachable_alternatives(alternatives: list[dict]) -> list[dict]:
  filtered: list[dict] = []
  for alt in alternatives:
    url = alt.get("product_url")
    if not isinstance(url, str):
      continue
    if await _is_reachable_url(url):
      filtered.append(alt)
  return filtered


async def _gemini_fallback_alternatives(item: Any, query: str) -> list[dict]:
  model = _get_gemini_model(settings.GEMINI_MODEL)
  if not model:
    return []

  prompt = f"""You are the Proposal Optimization Agent for an expense management system.

Find cheaper alternatives for:
  Item: {item.name}
  Current Price: {item.price}
  Search Query: {query}

Return a JSON array of 3-5 alternatives:
[
  {{
  "vendor": "Store Name",
  "price": 00.00,
  "rating": 4.5,
  "review_summary": "Brief summary",
  "product_url": "https://example.com/product",
  "source": "online"
  }}
]

Only include options with a valid absolute http/https product_url.
Do not fabricate stores or links. If no reliable options are available, return [].
Respond ONLY with the JSON array."""

  try:
    response = model.generate_content(prompt)
    alternatives = _safe_json_array(response.text)
    if not alternatives:
      return []
    normalized = _normalize_alternatives(alternatives, item.price)
    return await _filter_reachable_alternatives(normalized)
  except Exception as exc:
    logger.error("Gemini fallback alternatives error: %s", exc)
    return []
