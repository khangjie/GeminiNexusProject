from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel


class ReceiptItemUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    category: Optional[str] = None


class ReceiptItemRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    quantity: Optional[int]
    price: Optional[float]
    category: Optional[str]
    is_strikethrough: bool
    is_replacement: bool
    replacement_vendor: Optional[str]
    sort_order: int


class AIRuleCheckResultRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    rule_id: Optional[str]
    rule_text: str
    passed: bool
    explanation: Optional[str]


class ReceiptCreate(BaseModel):
    receipt_type: Literal["proposal", "paid_expense"] = "paid_expense"


class ReceiptRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    company_id: str
    worker_id: str
    vendor: Optional[str]
    total_amount: Optional[float]
    receipt_type: str
    status: str
    receipt_image_url: Optional[str]
    ai_verdict: Optional[str]
    ai_reason: Optional[str]
    rejection_reason: Optional[str]
    is_duplicate: bool
    duplicate_of_id: Optional[str]
    receipt_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    items: list[ReceiptItemRead] = []
    rule_check_results: list[AIRuleCheckResultRead] = []


class ReceiptProcessResult(BaseModel):
    """Returned after the OCR + AI pipeline completes."""
    receipt: ReceiptRead
    duplicate_warning: Optional[str] = None


class ProposalAlternativeItem(BaseModel):
    vendor: str
    price: float
    rating: Optional[float]
    review_summary: Optional[str]
    product_url: str
    source: Literal["online", "company_history"]


class ProposalAlternativeList(BaseModel):
    receipt_item_id: str
    item_name: str
    alternatives: list[ProposalAlternativeItem]
