"""
Gemini Service — thin compatibility shim.

All pipeline logic has moved to agents.*  This file re-exports the
public functions so that existing import sites (routes) continue to work
without changes.

    run_approval_pipeline      → agents.receipt_pipeline
    find_proposal_alternatives → agents.optimization_pipeline
    run_analytics_agent        → agents.analytics_pipeline
"""
from pathlib import Path
import sys

# Ensure repository root is importable so top-level `agents` package is available.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

from agents.receipt_pipeline import run_receipt_approval_pipeline as run_approval_pipeline  # noqa: F401
from agents.optimization_pipeline import run_proposal_optimization_pipeline as _run_opt
from agents.analytics_pipeline import run_expense_analytics_pipeline as _run_analytics
from app.schemas.analytics import AnalyticsResponse


async def find_proposal_alternatives(item, search_name, company_id) -> list:
    """Proxy to the ADK Proposal Optimization Pipeline."""
    return await _run_opt(item=item, search_name=search_name, company_id=company_id)


async def run_analytics_agent(
    question: str,
    receipts: list,
    db=None,
    company_id: str = "",
) -> AnalyticsResponse:
    """Proxy to the ADK Analytics Pipeline."""
    return await _run_analytics(
        question=question,
        receipts=receipts,
        db=db,
        company_id=company_id,
    )
