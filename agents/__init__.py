"""
ADK Multi-Agent Orchestration for the AI Expense Operations Hub.

Pipelines exposed by this package:

  run_receipt_approval_pipeline(receipt, db)
      → SequentialAgent (OCR Parser → Type Classifier)
        → ParallelAgent (Rule Checker | Pre-Approved Detector | Duplicate Detector)
        → Decision Agent
        → Categorization Agent

  run_proposal_optimization_pipeline(item, search_name, company_id)
      → SequentialAgent (Context Builder → Query Optimizer)
        → ParallelAgent (Google Search | Review Retrieval | RAG History)
        → Aggregation Agent
        → Recommendation Agent

  run_expense_analytics_pipeline(question, receipts)
      → SequentialAgent (Query Parser → Metric Extractor)
        → ParallelAgent (Data Query | Aggregation | Trend Analysis)
        → Insight Generation Agent
        → Chart Builder Agent
"""

from .receipt_pipeline import run_receipt_approval_pipeline
from .optimization_pipeline import run_proposal_optimization_pipeline
from .analytics_pipeline import run_expense_analytics_pipeline

__all__ = [
    "run_receipt_approval_pipeline",
    "run_proposal_optimization_pipeline",
    "run_expense_analytics_pipeline",
]
