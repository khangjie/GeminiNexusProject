"""
Receipt routes — upload, process (OCR + AI pipeline), list, update items.
"""
import os
import mimetypes
import logging
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.guardrails import guard_search_query
from app.core.security import get_current_user, require_owner
from app.models.receipt import Receipt, ReceiptItem
from app.models.user import User
from app.schemas.receipt import (
    ReceiptItemUpdate,
    ReceiptProcessResult,
    ReceiptRead,
    ProposalAlternativeList,
)
from app.services.ocr_service import extract_receipt_data
from app.services.gemini_service import run_approval_pipeline, find_proposal_alternatives

router = APIRouter(prefix="/receipts", tags=["receipts"])
logger = logging.getLogger(__name__)


def _receipt_upload_root() -> Path:
    root = Path(__file__).resolve().parents[3] / "storage" / "receipts"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sanitize_ext(filename: str | None, content_type: str | None) -> str:
    if filename and "." in filename:
        ext = Path(filename).suffix.lower()
        if ext and len(ext) <= 10:
            return ext
    guessed = mimetypes.guess_extension(content_type or "")
    return guessed or ".bin"


@router.post("/upload", response_model=ReceiptProcessResult, status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    file: UploadFile = File(...),
    receipt_type: str = Form("paid_expense"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a receipt image/PDF.
    Triggers the full OCR + multi-agent AI processing pipeline.
    """
    logger.info("Receipt upload requested by user_id=%s receipt_type=%s", current_user.id, receipt_type)

    if not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not assigned to a company")

    # Read file bytes
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10 MB cap
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 10MB)")

    # Step 1: OCR extraction via Cloud Vision AI
    try:
        logger.info("Running OCR extraction for user_id=%s", current_user.id)
        ocr_data = await extract_receipt_data(file_bytes, file.content_type or "image/jpeg")
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    # Step 2: Create receipt record
    receipt = Receipt(
        company_id=current_user.company_id,
        worker_id=current_user.id,
        receipt_type=receipt_type,
        receipt_image_url=None,
        vendor=ocr_data.get("vendor"),
        total_amount=ocr_data.get("total_amount"),
        ocr_raw_text=ocr_data.get("raw_text"),
        receipt_date=ocr_data.get("date"),
    )
    db.add(receipt)
    db.flush()
    logger.info("Receipt draft created receipt_id=%s company_id=%s", receipt.id, current_user.company_id)

    ext = _sanitize_ext(file.filename, file.content_type)
    company_dir = _receipt_upload_root() / str(current_user.company_id)
    company_dir.mkdir(parents=True, exist_ok=True)
    file_path = company_dir / f"{receipt.id}{ext}"
    file_path.write_bytes(file_bytes)
    receipt.receipt_image_url = f"/api/v1/receipts/{receipt.id}/image"

    # Step 3: Persist extracted items
    for i, item_data in enumerate(ocr_data.get("items", [])):
        item = ReceiptItem(
            receipt_id=receipt.id,
            name=item_data.get("name", "Unknown Item"),
            quantity=item_data.get("quantity"),
            price=item_data.get("price"),
            sort_order=i,
        )
        db.add(item)

    db.flush()

    # Step 4: Run the ADK multi-agent approval pipeline (async)
    logger.info("Starting approval pipeline for receipt_id=%s", receipt.id)
    pipeline_result = await run_approval_pipeline(receipt, db)
    logger.info(
        "Approval pipeline finished for receipt_id=%s status=%s verdict=%s",
        receipt.id,
        pipeline_result.get("status"),
        pipeline_result.get("verdict"),
    )

    receipt.status = pipeline_result["status"]
    receipt.ai_verdict = pipeline_result.get("verdict")
    receipt.ai_reason = pipeline_result.get("reason")
    receipt.is_duplicate = pipeline_result.get("is_duplicate", False)
    receipt.duplicate_of_id = pipeline_result.get("duplicate_of_id")

    # Persist AI rule check results
    for check in pipeline_result.get("rule_checks", []):
        from app.models.receipt import AIRuleCheckResult
        result = AIRuleCheckResult(
            receipt_id=receipt.id,
            rule_id=check.get("rule_id"),
            rule_text=check["rule_text"],
            passed=check["passed"],
            explanation=check.get("explanation"),
        )
        db.add(result)

    db.commit()
    db.refresh(receipt)

    # Step 5: Upsert receipt embedding into Qdrant for future RAG lookups
    from app.services.rag_service import upsert_receipt_embedding
    import asyncio
    embed_text = f"{receipt.vendor} {receipt.ocr_raw_text or ''}"
    asyncio.ensure_future(upsert_receipt_embedding(
        receipt_id=receipt.id,
        text=embed_text,
        company_id=receipt.company_id,
        vendor=receipt.vendor or "",
        price=receipt.total_amount,
        date=str(receipt.receipt_date or ""),
        item_name=" ".join(i.name for i in receipt.items),
    ))

    duplicate_warning = None
    if receipt.is_duplicate and receipt.duplicate_of_id:
        duplicate_warning = f"Possible duplicate of receipt {receipt.duplicate_of_id}"

    logger.info("Receipt processing completed receipt_id=%s", receipt.id)

    return ReceiptProcessResult(receipt=ReceiptRead.model_validate(receipt), duplicate_warning=duplicate_warning)


@router.get("/", response_model=list[ReceiptRead])
def list_receipts(
    receipt_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List receipts for the current user's company."""
    if not current_user.company_id:
        return []
    query = db.query(Receipt).filter(Receipt.company_id == current_user.company_id)
    if receipt_type:
        query = query.filter(Receipt.receipt_type == receipt_type)
    if status:
        query = query.filter(Receipt.status == status)
    # Workers only see their own receipts
    if current_user.role == "worker":
        query = query.filter(Receipt.worker_id == current_user.id)
    return query.order_by(Receipt.created_at.desc()).all()


@router.get("/{receipt_id}", response_model=ReceiptRead)
def get_receipt(receipt_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt or receipt.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    return receipt


@router.get("/{receipt_id}/image")
def get_receipt_image(receipt_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt or receipt.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")

    company_dir = _receipt_upload_root() / str(receipt.company_id)
    candidates = list(company_dir.glob(f"{receipt.id}.*"))
    if not candidates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt file not found")

    file_path = candidates[0]
    media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    return FileResponse(path=file_path, media_type=media_type, filename=file_path.name)


@router.patch("/{receipt_id}/items/{item_id}", response_model=ReceiptRead)
def update_receipt_item(
    receipt_id: str,
    item_id: str,
    body: ReceiptItemUpdate,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    """Owner can edit extracted item details."""
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id, Receipt.company_id == current_user.company_id).first()
    if not receipt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    item = db.query(ReceiptItem).filter(ReceiptItem.id == item_id, ReceiptItem.receipt_id == receipt_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if body.name is not None:
        item.name = body.name
    if body.quantity is not None:
        item.quantity = body.quantity
    if body.price is not None:
        item.price = body.price
    if body.category is not None:
        item.category = body.category
    db.commit()
    db.refresh(receipt)
    return receipt


@router.post("/{receipt_id}/items/{item_id}/alternatives", response_model=ProposalAlternativeList)
async def get_item_alternatives(
    receipt_id: str,
    item_id: str,
    search_name: Optional[str] = None,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    """
    Proposal price comparison — runs the Proposal Optimization Agent.
    Searches online + company RAG history for cheaper alternatives.
    """
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id, Receipt.company_id == current_user.company_id).first()
    if not receipt or receipt.receipt_type != "proposal":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Receipt not found or not a proposal")
    item = db.query(ReceiptItem).filter(ReceiptItem.id == item_id, ReceiptItem.receipt_id == receipt_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    safe_search_name = guard_search_query(search_name) if search_name else None
    alternatives = await find_proposal_alternatives(item, safe_search_name, current_user.company_id)
    return ProposalAlternativeList(receipt_item_id=item_id, item_name=item.name, alternatives=alternatives)


@router.post("/{receipt_id}/items/{item_id}/apply-replacement")
def apply_replacement(
    receipt_id: str,
    item_id: str,
    vendor: str,
    new_price: float,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    """Apply a selected alternative as the replacement for a proposal item."""
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id, Receipt.company_id == current_user.company_id).first()
    if not receipt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    item = db.query(ReceiptItem).filter(ReceiptItem.id == item_id, ReceiptItem.receipt_id == receipt_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # Strike-through original item
    item.is_strikethrough = True
    db.flush()

    # Add replacement item
    replacement = ReceiptItem(
        receipt_id=receipt_id,
        name=f"{item.name} (Replacement)",
        price=new_price,
        is_replacement=True,
        replacement_vendor=vendor,
        sort_order=item.sort_order + 1,
    )
    db.add(replacement)
    db.commit()
    db.refresh(receipt)
    return ReceiptRead.model_validate(receipt)
