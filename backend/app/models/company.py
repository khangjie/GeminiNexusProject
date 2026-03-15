import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    members: Mapped[list["User"]] = relationship("User", back_populates="company", foreign_keys="User.company_id")
    receipts: Mapped[list["Receipt"]] = relationship("Receipt", back_populates="company")
    approval_rules: Mapped[list["ApprovalRule"]] = relationship("ApprovalRule", back_populates="company")
    pre_approved_items: Mapped[list["PreApprovedItem"]] = relationship("PreApprovedItem", back_populates="company")
    expense_categories: Mapped[list["ExpenseCategory"]] = relationship("ExpenseCategory", back_populates="company")
