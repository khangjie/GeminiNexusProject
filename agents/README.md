# Agents — ADK Multi-Agent Orchestration

This directory documents the multi-agent architecture.
The implementation lives in `agents/`.

## Architecture Overview

```
agents/
├── __init__.py                 # Public API: run_*_pipeline()
├── _runner.py                  # ADK import guard + runner utility
├── tools.py                    # ADK FunctionTool definitions (DB, RAG)
├── receipt_pipeline.py         # Auto-approval pipeline
├── optimization_pipeline.py    # Proposal price comparison pipeline
└── analytics_pipeline.py       # Company expense analytics pipeline
```

## Pipeline 1 — Receipt Auto-Approval

```
SequentialAgent: receipt_processing_pipeline
│
├── SequentialAgent: extraction_pipeline
│       ├── receipt_parser_agent
│       └── receipt_type_classifier
│
├── ParallelAgent: validation_pipeline
│       ├── rule_checker_agent          ← uses fetch_approval_rules tool
│       ├── pre_approved_detector       ← uses fetch_pre_approved_items tool
│       └── duplicate_detector          ← uses fetch_recent_receipts tool
│
├── decision_agent
└── categorization_agent
```

## Pipeline 2 — Proposal Price Comparison / Replacement

```
SequentialAgent: item_optimization_pipeline
│
├── SequentialAgent: item_context_pipeline
│       ├── context_builder_agent
│       └── search_query_optimizer_agent
│
├── ParallelAgent: market_search_pipeline
│       ├── google_search_agent
│       ├── review_retrieval_agent
│       └── rag_receipt_history_agent   ← uses search_company_purchase_history tool (RAG)
│
├── alternative_aggregation_agent
└── recommendation_agent
```

## Pipeline 3 — Company Expense Analytics

```
SequentialAgent: analytics_pipeline
│
├── SequentialAgent: query_understanding_pipeline
│       ├── nl_query_parser_agent
│       └── metric_extractor_agent
│
├── ParallelAgent: data_retrieval_pipeline
│       ├── expense_data_query_agent    ← uses fetch_expense_data tool
│       ├── expense_aggregation_agent
│       └── trend_analysis_agent
│
├── insight_generation_agent
└── chart_data_builder_agent
```

## Fallback Strategy

All pipelines degrade gracefully:
1. **ADK available + API key**: Full ADK multi-agent execution via `google.adk`
2. **ADK unavailable**: Direct `google.generativeai` single-prompt fallback
3. **No API key**: Mock responses (for local development without GCP credentials)

## Agent Framework: Google ADK

- Package: `google-adk >= 0.1.0`
- Agents: `google.adk.agents.Agent`, `SequentialAgent`, `ParallelAgent`
- Tools: `google.adk.tools.FunctionTool`
- Runner: `google.adk.runners.Runner` + `InMemorySessionService`
- Model: Gemini 1.5 Flash (configurable via `GEMINI_MODEL` env var)
