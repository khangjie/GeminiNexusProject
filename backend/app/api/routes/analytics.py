"""
Analytics routes — AI-powered natural language expense querying.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.guardrails import guard_analytics_query
from app.core.security import require_owner
from app.models.receipt import Receipt, ReceiptItem
from app.models.user import User
from app.schemas.analytics import AnalyticsQuery, AnalyticsResponse
from app.services.gemini_service import run_analytics_agent

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/query", response_model=AnalyticsResponse)
async def analytics_query(
    body: AnalyticsQuery,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    """
    Natural language analytics query.
    The Analytics Agent pipeline parses the question, queries the DB,
    aggregates results, and returns an insight + optional chart data.
    """
    if not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner not associated with a company")

    # Fetch approved expense data for context
    receipts = (
        db.query(Receipt)
        .filter(
            Receipt.company_id == current_user.company_id,
            Receipt.status.in_(["approved", "ai_approved"]),
        )
        .order_by(Receipt.created_at.desc())
        .limit(500)
        .all()
    )

    safe_question = guard_analytics_query(body.question)

    response = await run_analytics_agent(
        safe_question,
        receipts,
        db=db,
        company_id=current_user.company_id,
    )
    return response


@router.get("/summary")
def analytics_summary(
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    """
    Quick summary stats for the owner dashboard:
    total spend, pending count, AI approval rate, savings vs proposals.
    """
    from sqlalchemy import func

    company_id = current_user.company_id
    if not company_id:
        return {}

    total_spend = (
        db.query(func.sum(Receipt.total_amount))
        .filter(Receipt.company_id == company_id, Receipt.status.in_(["approved", "ai_approved"]))
        .scalar()
        or 0.0
    )
    pending_count = (
        db.query(func.count(Receipt.id))
        .filter(Receipt.company_id == company_id, Receipt.status == "awaiting")
        .scalar()
        or 0
    )
    total_processed = (
        db.query(func.count(Receipt.id))
        .filter(Receipt.company_id == company_id, Receipt.status != "awaiting")
        .scalar()
        or 1
    )
    ai_approved_count = (
        db.query(func.count(Receipt.id))
        .filter(Receipt.company_id == company_id, Receipt.status == "ai_approved")
        .scalar()
        or 0
    )
    ai_approval_rate = round((ai_approved_count / total_processed) * 100, 1)

    return {
        "total_spend": total_spend,
        "pending_count": pending_count,
        "ai_approval_rate": ai_approval_rate,
    }
