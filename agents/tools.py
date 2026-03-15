"""
ADK Function Tools — Python functions wrapped as ADK FunctionTool objects.

Tools use context vars so agent pipelines can inject the database session
and company context without passing them through ADK's conversation layer.

Usage pattern:
    from agents.tools import set_pipeline_context, get_all_tools

    set_pipeline_context(db=db_session, company_id="abc-123")
    tools = get_all_tools()          # → list[FunctionTool]
"""
from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from typing import Any

from agents._runner import ADK_AVAILABLE, FunctionTool

logger = logging.getLogger(__name__)

# ── Context vars ─────────────────────────────────────────────────────────────
_db_ctx: ContextVar[Any] = ContextVar("db_ctx", default=None)
_company_id_ctx: ContextVar[str] = ContextVar("company_id_ctx", default="")


def set_pipeline_context(db: Any, company_id: str) -> None:
    """Call before running a pipeline to inject DB session + company scope."""
    _db_ctx.set(db)
    _company_id_ctx.set(company_id)


# ── Tool functions ────────────────────────────────────────────────────────────

def fetch_approval_rules() -> str:
    """
    Fetch the list of active auto-approval rules defined by the company owner.
    Returns a JSON array where each element has: id, name, prompt.
    Use this to evaluate whether a receipt satisfies each rule.
    """
    db = _db_ctx.get()
    company_id = _company_id_ctx.get()
    if not db or not company_id:
        return "[]"
    try:
        from app.models.approval_rule import ApprovalRule
        from app.core.approval_rule_meta import decode_approval_rule_prompt
        rules = db.query(ApprovalRule).filter(
            ApprovalRule.company_id == company_id,
            ApprovalRule.is_active == True,
        ).all()
        return json.dumps([
            {
                "id": r.id,
                "name": r.name,
                "prompt": decode_approval_rule_prompt(r.prompt)[0],
                "applies_to_preapproved": decode_approval_rule_prompt(r.prompt)[1],
            }
            for r in rules
        ])
    except Exception as exc:
        logger.error("fetch_approval_rules error: %s", exc)
        return "[]"


def fetch_pre_approved_items() -> str:
    """
    Fetch the company's pre-approved item configurations.
    Returns a JSON array where each element has: id, item_name, amount_limit, note.
    Use this to detect if any receipt items match pre-approved definitions.
    """
    db = _db_ctx.get()
    company_id = _company_id_ctx.get()
    if not db or not company_id:
        return "[]"
    try:
        from app.models.pre_approved_item import PreApprovedItem
        from app.core.pre_approved_meta import decode_pre_approved_meta
        items = db.query(PreApprovedItem).filter(
            PreApprovedItem.company_id == company_id,
            PreApprovedItem.is_active == True,
        ).all()
        return json.dumps([
            {
                "id": i.id,
                "item_name": i.item_name,
                "amount_limit": i.amount_limit,
                "note": decode_pre_approved_meta(i.note)[0],
                "custom_variables": decode_pre_approved_meta(i.note)[1],
            }
            for i in items
        ])
    except Exception as exc:
        logger.error("fetch_pre_approved_items error: %s", exc)
        return "[]"


def fetch_recent_receipts(limit: int = 30) -> str:
    """
    Fetch recent receipts from the company's records for duplicate detection.
    Returns a JSON array where each element has: id, vendor, total_amount, receipt_date.
    Use this to compare the current receipt and flag potential duplicates.
    """
    db = _db_ctx.get()
    company_id = _company_id_ctx.get()
    if not db or not company_id:
        return "[]"
    try:
        from app.models.receipt import Receipt
        receipts = db.query(Receipt).filter(
            Receipt.company_id == company_id,
        ).order_by(Receipt.created_at.desc()).limit(limit).all()
        return json.dumps([
            {
                "id": r.id,
                "vendor": r.vendor,
                "total_amount": r.total_amount,
                "receipt_date": str(r.receipt_date),
            }
            for r in receipts
        ])
    except Exception as exc:
        logger.error("fetch_recent_receipts error: %s", exc)
        return "[]"


def fetch_expense_data(limit: int = 100) -> str:
    """
    Fetch approved expense records for analytics and reporting.
    Returns a JSON array where each element has: id, vendor, receipt_type,
    total_amount, receipt_date, status.
    Use this when answering analytics questions about company spending.
    """
    db = _db_ctx.get()
    company_id = _company_id_ctx.get()
    if not db or not company_id:
        return "[]"
    try:
        from app.models.receipt import Receipt
        receipts = db.query(Receipt).filter(
            Receipt.company_id == company_id,
            Receipt.status.in_(["approved", "ai_approved"]),
        ).order_by(Receipt.created_at.desc()).limit(limit).all()
        return json.dumps([
            {
                "id": r.id,
                "vendor": r.vendor,
                "receipt_type": r.receipt_type,
                "total_amount": r.total_amount,
                "receipt_date": str(r.receipt_date),
                "status": r.status,
            }
            for r in receipts
        ])
    except Exception as exc:
        logger.error("fetch_expense_data error: %s", exc)
        return "[]"


async def search_company_purchase_history(item_name: str) -> str:
    """
    Search the company's purchase history using RAG (Retrieval-Augmented Generation)
    for items similar to item_name.
    Returns a JSON array of past purchase records with vendor, price, and date.
    Use this when finding alternative options for proposal items.
    """
    try:
        from app.services.rag_service import search_purchase_history
        company_id = _company_id_ctx.get() or "unknown"
        results = await search_purchase_history(item_name, company_id)
        return json.dumps(results)
    except Exception as exc:
        logger.error("search_company_purchase_history error: %s", exc)
        return "[]"


# ── FunctionTool wrappers (built only if ADK is available) ────────────────────

def _make_tool(fn) -> Any:
    """Wrap a Python function as an ADK FunctionTool, or return the raw callable."""
    if ADK_AVAILABLE and FunctionTool is not None:
        return FunctionTool(func=fn)
    return fn


approval_rules_tool = _make_tool(fetch_approval_rules)
pre_approved_items_tool = _make_tool(fetch_pre_approved_items)
recent_receipts_tool = _make_tool(fetch_recent_receipts)
expense_data_tool = _make_tool(fetch_expense_data)
rag_history_tool = _make_tool(search_company_purchase_history)
