"""
Analytics Pipeline — ADK multi-agent implementation.

Company Expense Analyzer Flow (matches ProjectStructure.litcoffee):

  Owner Asks Analytics Question
          │
          ▼
  SequentialAgent: query_understanding_pipeline
          ├── query_parser_agent          (detect intent: trend | comparison | summary)
          └── metric_extractor_agent      (extract category, time range, filters)
          │
          ▼
  ParallelAgent: data_retrieval_pipeline
          ├── expense_data_query_agent    (retrieve expense records via DB tool)
          ├── aggregation_agent           (calculate totals, averages, category spending)
          └── trend_analysis_agent        (detect increase/decrease patterns)
          │
          ▼
  insight_gen_agent                       (generate explanation, highlight patterns)
          │
          ▼
  chart_builder_agent                     (format data for charts, select template)

Public API:
    run_expense_analytics_pipeline(question, receipts) -> AnalyticsResponse
"""
from __future__ import annotations

import logging
from typing import Any

from agents._runner import (
    ADK_AVAILABLE,
    Agent,
    ParallelAgent,
    SequentialAgent,
    _get_gemini_model,
    _safe_json,
    run_adk_pipeline,
)
from agents.tools import expense_data_tool, set_pipeline_context
from app.core.config import get_settings
from app.schemas.analytics import AnalyticsResponse, ChartDataPoint

logger = logging.getLogger(__name__)
settings = get_settings()
MODEL = settings.GEMINI_MODEL


# ── Agent Definitions ─────────────────────────────────────────────────────────

def _build_agents():
    if not ADK_AVAILABLE:
        return None

    # 1. NL Query Parser — detect intent
    query_parser = Agent(
        name="nl_query_parser_agent",
        model=MODEL,
        instruction="""You are the Natural Language Query Parser Agent for company expense analytics.

Analyze the user's analytics question and determine:
  - intent: "trend" | "comparison" | "summary" | "anomaly" | "breakdown"
  - subject: what they are asking about (category, vendor, time, etc.)

Respond with a JSON object:
{
  "intent": "trend" | "comparison" | "summary" | "anomaly" | "breakdown",
  "subject": "description of what is being queried",
  "requires_chart": true | false,
  "chart_type_hint": "bar" | "line" | "pie" | null,
  "complexity": "simple" | "complex"
}

Output ONLY the JSON object.
""",
        output_key="query_intent",
    )

    # 2. Metric Extractor — extract dimensions, time range, filters
    metric_extractor = Agent(
        name="metric_extractor_agent",
        model=MODEL,
        instruction="""You are the Metric Extraction Agent.

Based on the parsed query intent, extract specific metrics, dimensions, and
filters needed to answer the analytics question.

Respond with a JSON object:
{
  "metrics": ["total_spend", "average_spend", "count", etc.],
  "dimensions": ["category", "vendor", "month", etc.],
  "time_range": { "start": "YYYY-MM" | null, "end": "YYYY-MM" | null },
  "filters": { "category": "..." | null, "vendor": "..." | null },
  "group_by": "category" | "vendor" | "month" | "receipt_type" | null
}

Output ONLY the JSON object.
""",
        output_key="query_metrics",
    )

    # 3. Expense Data Query Agent — retrieves records via tool
    expense_query = Agent(
        name="expense_data_query_agent",
        model=MODEL,
        instruction="""You are the Expense Data Query Agent.

Use the `fetch_expense_data` tool to retrieve the company's approved expense
records from the database.

After fetching, summarize the raw data in a compact format for downstream agents:
- Total number of records
- Date range
- Total spend
- Top 5 vendors by spend

Respond with a JSON object containing this summary plus the raw data reference.
Output ONLY the JSON object.
""",
        tools=[expense_data_tool],
        output_key="expense_data_summary",
    )

    # 4. Aggregation Agent — compute totals, averages, breakdowns
    aggregation = Agent(
        name="expense_aggregation_agent",
        model=MODEL,
        instruction="""You are the Expense Aggregation Agent.

Based on the expense data and query metrics from earlier in this conversation,
calculate the requested aggregations.

Respond with a JSON object:
{
  "totals": { "key": value, ... },
  "averages": { "key": value, ... },
  "breakdowns": [
    { "label": "...", "value": 0.00, "percentage": 0.0 }
  ],
  "top_items": [
    { "label": "...", "value": 0.00 }
  ]
}

Output ONLY the JSON object.
""",
        output_key="aggregation_results",
    )

    # 5. Trend Analysis Agent
    trend_analysis = Agent(
        name="trend_analysis_agent",
        model=MODEL,
        instruction="""You are the Trend Analysis Agent.

Based on the expense data from this conversation, identify trends, patterns,
and anomalies in company spending.

Respond with a JSON object:
{
  "trends": [
    {
      "description": "...",
      "direction": "increasing" | "decreasing" | "stable",
      "magnitude": "significant" | "moderate" | "minor",
      "time_period": "..."
    }
  ],
  "anomalies": [
    { "description": "...", "severity": "high" | "medium" | "low" }
  ],
  "key_insight": "single most important finding"
}

Output ONLY the JSON object.
""",
        output_key="trend_results",
    )

    # 6. Insight Generation Agent
    insight_gen = Agent(
        name="insight_generation_agent",
        model=MODEL,
        instruction="""You are the Insight Generation Agent.

You have access to aggregation results and trend analysis from this conversation.
Synthesize everything into a clear, actionable answer for the company owner.

Respond with a JSON object:
{
  "answer": "Clear, natural language answer to the original question (2-4 sentences)",
  "key_points": ["bullet point 1", "bullet point 2", "bullet point 3"],
  "recommendation": "optional actionable recommendation" | null
}

Output ONLY the JSON object.
""",
        output_key="insights",
    )

    # 7. Chart Builder Agent
    chart_builder = Agent(
        name="chart_data_builder_agent",
        model=MODEL,
        instruction="""You are the Chart Data Builder Agent.

Based on the aggregation results from this conversation, determine the best
chart to visualize the data and format it for frontend rendering.

Respond with a JSON object:
{
  "chart_type": "bar" | "line" | "pie" | null,
  "chart_title": "descriptive chart title",
  "chart_data": [
    { "label": "Category/Date/Vendor", "value": 0.00 }
  ]
}

Only include chart_data if a chart would meaningfully add to the answer.
If no chart is needed, set chart_type to null and chart_data to null.

Output ONLY the JSON object.
""",
        output_key="chart_data",
    )

    return {
        "query_parser": query_parser,
        "metric_extractor": metric_extractor,
        "expense_query": expense_query,
        "aggregation": aggregation,
        "trend_analysis": trend_analysis,
        "insight_gen": insight_gen,
        "chart_builder": chart_builder,
    }


def _build_pipeline(agents: dict):
    query_understanding_pipeline = SequentialAgent(
        name="query_understanding_pipeline",
        description="Parses the analytics question and extracts required metrics.",
        sub_agents=[
            agents["query_parser"],
            agents["metric_extractor"],
        ],
    )

    data_retrieval_pipeline = ParallelAgent(
        name="data_retrieval_pipeline",
        description="Retrieves expense data, computes aggregations, and detects trends in parallel.",
        sub_agents=[
            agents["expense_query"],
            agents["aggregation"],
            agents["trend_analysis"],
        ],
    )

    return SequentialAgent(
        name="analytics_pipeline",
        description="Full company expense analytics pipeline.",
        sub_agents=[
            query_understanding_pipeline,
            data_retrieval_pipeline,
            agents["insight_gen"],
            agents["chart_builder"],
        ],
    )


# ── Public pipeline runner ────────────────────────────────────────────────────

async def run_expense_analytics_pipeline(
    question: str,
    receipts: list,
    db: Any = None,
    company_id: str = "",
) -> AnalyticsResponse:
    """
    Run the full ADK analytics pipeline against company expense data.

    Falls back to direct Gemini prompts if ADK is unavailable.
    """
    set_pipeline_context(db=db, company_id=company_id)

    # Compact receipts summary for context
    receipts_summary = "\n".join(
        f"- {r.vendor} | {r.receipt_type} | {r.total_amount} | {r.receipt_date} | {r.status}"
        for r in receipts[:100]
    ) or "No expense data available."

    initial_prompt = f"""Company expense analytics question:
"{question}"

Available expense records (up to 100 most recent approved):
{receipts_summary}

Please analyze and answer this question using the full analytics pipeline."""

    # ── Try ADK pipeline ──────────────────────────────────────────────────────
    if ADK_AVAILABLE:
        try:
            agents = _build_agents()
            pipeline = _build_pipeline(agents)
            final_text = await run_adk_pipeline(pipeline, initial_prompt)
            return _parse_analytics_response(final_text)
        except Exception as exc:
            logger.warning("ADK analytics pipeline failed (%s), using Gemini fallback.", exc)

    # ── Gemini direct fallback ────────────────────────────────────────────────
    return await _gemini_fallback_analytics(question, receipts_summary)


def _parse_analytics_response(text: str) -> AnalyticsResponse:
    """Extract the analytics response from the chart_builder agent's JSON output."""
    result = _safe_json(text)

    chart_data = None
    if result.get("chart_data"):
        chart_data = [
            ChartDataPoint(label=d["label"], value=float(d["value"]))
            for d in result["chart_data"]
            if "label" in d and "value" in d
        ]

    # The answer may come from chart_builder (which includes insights) or insights
    answer = result.get("answer") or result.get("key_insight") or "Analysis complete."

    return AnalyticsResponse(
        answer=answer,
        chart_type=result.get("chart_type"),
        chart_title=result.get("chart_title"),
        chart_data=chart_data,
    )


async def _gemini_fallback_analytics(question: str, receipts_summary: str) -> AnalyticsResponse:
    model = _get_gemini_model(settings.GEMINI_MODEL)
    if not model:
        return AnalyticsResponse(answer="AI service unavailable. Please configure GOOGLE_API_KEY.")

    prompt = f"""You are the Company Expense Analytics Agent.

Expense data:
{receipts_summary}

Question: {question}

Respond with ONLY a JSON object:
{{
  "answer": "Clear natural language answer",
  "chart_type": "bar" | "line" | "pie" | null,
  "chart_title": "title" | null,
  "chart_data": [
    {{"label": "...", "value": 0.00}}
  ] | null
}}"""

    try:
        response = model.generate_content(prompt)
        result = _safe_json(response.text)
    except Exception as exc:
        logger.error("Gemini analytics fallback error: %s", exc)
        result = {}

    chart_data = None
    if result.get("chart_data"):
        chart_data = [
            ChartDataPoint(label=d["label"], value=float(d["value"]))
            for d in result["chart_data"]
            if "label" in d and "value" in d
        ]

    return AnalyticsResponse(
        answer=result.get("answer", "Unable to generate answer."),
        chart_type=result.get("chart_type"),
        chart_title=result.get("chart_title"),
        chart_data=chart_data,
    )
