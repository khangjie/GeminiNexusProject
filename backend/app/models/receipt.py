import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Float, JSON, Text, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.user import User


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    worker_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    # "proposal" or "paid_expense"
    receipt_type: Mapped[str] = mapped_column(
        SAEnum("proposal", "paid_expense", name="receipt_type_enum"), nullable=False, default="paid_expense"
    )

    # "awaiting" | "ai_approved" | "ai_rejected" | "approved" | "rejected"
    status: Mapped[str] = mapped_column(
        SAEnum("awaiting", "ai_approved", "ai_rejected", "approved", "rejected", name="receipt_status_enum"),
        nullable=False,
        default="awaiting",
    )

    receipt_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ocr_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_verdict: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("receipts.id"), nullable=True)

    receipt_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    company: Mapped["Company"] = relationship("Company", back_populates="receipts")
    worker: Mapped["User"] = relationship("User", back_populates="submitted_receipts")
    items: Mapped[list["ReceiptItem"]] = relationship("ReceiptItem", back_populates="receipt", cascade="all, delete-orphan")
    rule_check_results: Mapped[list["AIRuleCheckResult"]] = relationship(
        "AIRuleCheckResult", back_populates="receipt", cascade="all, delete-orphan"
    )


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    receipt_id: Mapped[str] = mapped_column(String(36), ForeignKey("receipts.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int | None] = mapped_column(nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_strikethrough: Mapped[bool] = mapped_column(Boolean, default=False)
    is_replacement: Mapped[bool] = mapped_column(Boolean, default=False)
    replacement_vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0)

    receipt: Mapped["Receipt"] = relationship("Receipt", back_populates="items")


class AIRuleCheckResult(Base):
    __tablename__ = "ai_rule_check_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    receipt_id: Mapped[str] = mapped_column(String(36), ForeignKey("receipts.id"), nullable=False)
    rule_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("approval_rules.id"), nullable=True)
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    receipt: Mapped["Receipt"] = relationship("Receipt", back_populates="rule_check_results")
