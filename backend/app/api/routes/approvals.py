"""
Approvals routes — owner reviews AI decisions and approves/rejects.
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_owner
from app.models.receipt import Receipt
from app.models.user import User
from app.schemas.receipt import ReceiptRead

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: Optional[str] = None


@router.get("/", response_model=list[ReceiptRead])
def list_approvals(
    queue: Optional[str] = None,       # "awaiting" | "ai_approved" | "ai_rejected"
    receipt_type: Optional[str] = None,  # "proposal" | "paid_expense"
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    """
    Returns receipts for the approval queue.
    - queue: filter by AI decision status
    - receipt_type: filter by Proposal or Paid Expense
    """
    query = db.query(Receipt).filter(Receipt.company_id == current_user.company_id)
    if queue:
        query = query.filter(Receipt.status == queue)
    else:
        # Default: everything that needs attention
        query = query.filter(Receipt.status.in_(["awaiting", "ai_approved", "ai_rejected"]))
    if receipt_type:
        query = query.filter(Receipt.receipt_type == receipt_type)
    return query.order_by(Receipt.created_at.desc()).all()


@router.post("/{receipt_id}/decide", response_model=ReceiptRead)
def decide_receipt(
    receipt_id: str,
    body: ApprovalDecision,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    """Owner manually approves or rejects a receipt, overriding AI decision."""
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id, Receipt.company_id == current_user.company_id
    ).first()
    if not receipt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")

    receipt.status = body.decision
    if body.decision == "rejected" and body.reason:
        receipt.rejection_reason = body.reason
    db.commit()
    db.refresh(receipt)
    return receipt
