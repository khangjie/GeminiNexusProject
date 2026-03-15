"""
Settings routes — approval rules, pre-approved items, workers management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.approval_rule_meta import decode_approval_rule_prompt, encode_approval_rule_prompt
from app.core.pre_approved_meta import decode_pre_approved_meta, encode_pre_approved_meta
from app.core.security import require_owner
from app.models.approval_rule import ApprovalRule
from app.models.pre_approved_item import PreApprovedItem
from app.models.user import User
from app.schemas.approval_rule import ApprovalRuleCreate, ApprovalRuleRead, ApprovalRuleUpdate
from app.schemas.pre_approved_item import PreApprovedItemCreate, PreApprovedItemRead, PreApprovedItemUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _to_pre_approved_read(item: PreApprovedItem) -> PreApprovedItemRead:
    note, custom_variables = decode_pre_approved_meta(item.note)
    return PreApprovedItemRead(
        id=item.id,
        company_id=item.company_id,
        item_name=item.item_name,
        amount_limit=item.amount_limit,
        note=note,
        custom_variables=custom_variables or None,
        is_active=item.is_active,
        created_at=item.created_at,
    )


def _to_approval_rule_read(rule: ApprovalRule) -> ApprovalRuleRead:
    prompt, applies_to_preapproved = decode_approval_rule_prompt(rule.prompt)
    return ApprovalRuleRead(
        id=rule.id,
        company_id=rule.company_id,
        name=rule.name,
        prompt=prompt,
        applies_to_preapproved=applies_to_preapproved,
        is_active=rule.is_active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


# ── Approval Rules ──────────────────────────────────────────────────────────

@router.get("/rules", response_model=list[ApprovalRuleRead])
def list_rules(current_user: User = Depends(require_owner), db: Session = Depends(get_db)):
    rules = db.query(ApprovalRule).filter(ApprovalRule.company_id == current_user.company_id).all()
    return [_to_approval_rule_read(rule) for rule in rules]


@router.post("/rules", response_model=ApprovalRuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(body: ApprovalRuleCreate, current_user: User = Depends(require_owner), db: Session = Depends(get_db)):
    payload = body.model_dump(exclude={"applies_to_preapproved"})
    payload["prompt"] = encode_approval_rule_prompt(body.prompt, body.applies_to_preapproved)
    rule = ApprovalRule(company_id=current_user.company_id, **payload)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _to_approval_rule_read(rule)


@router.patch("/rules/{rule_id}", response_model=ApprovalRuleRead)
def update_rule(
    rule_id: str, body: ApprovalRuleUpdate, current_user: User = Depends(require_owner), db: Session = Depends(get_db)
):
    rule = db.query(ApprovalRule).filter(
        ApprovalRule.id == rule_id,
        ApprovalRule.company_id == current_user.company_id,
    ).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    payload = body.model_dump(exclude_none=True)
    current_prompt, current_applies = decode_approval_rule_prompt(rule.prompt)
    applies_to_preapproved = payload.pop("applies_to_preapproved", current_applies)
    prompt_to_store = payload.pop("prompt", current_prompt)

    for field, value in payload.items():
        setattr(rule, field, value)
    rule.prompt = encode_approval_rule_prompt(prompt_to_store, applies_to_preapproved)
    db.commit()
    db.refresh(rule)
    return _to_approval_rule_read(rule)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: str, current_user: User = Depends(require_owner), db: Session = Depends(get_db)):
    rule = db.query(ApprovalRule).filter(
        ApprovalRule.id == rule_id,
        ApprovalRule.company_id == current_user.company_id,
    ).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    db.delete(rule)
    db.commit()


# ── Pre-Approved Items ───────────────────────────────────────────────────────

@router.get("/pre-approved", response_model=list[PreApprovedItemRead])
def list_pre_approved(current_user: User = Depends(require_owner), db: Session = Depends(get_db)):
    items = db.query(PreApprovedItem).filter(PreApprovedItem.company_id == current_user.company_id).all()
    return [_to_pre_approved_read(item) for item in items]


@router.post("/pre-approved", response_model=PreApprovedItemRead, status_code=status.HTTP_201_CREATED)
def create_pre_approved(body: PreApprovedItemCreate, current_user: User = Depends(require_owner), db: Session = Depends(get_db)):
    payload = body.model_dump(exclude={"custom_variables"})
    payload["note"] = encode_pre_approved_meta(body.note, body.custom_variables)
    item = PreApprovedItem(company_id=current_user.company_id, **payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_pre_approved_read(item)


@router.patch("/pre-approved/{item_id}", response_model=PreApprovedItemRead)
def update_pre_approved(
    item_id: str, body: PreApprovedItemUpdate, current_user: User = Depends(require_owner), db: Session = Depends(get_db)
):
    item = db.query(PreApprovedItem).filter(PreApprovedItem.id == item_id, PreApprovedItem.company_id == current_user.company_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pre-approved item not found")

    payload = body.model_dump(exclude_none=True)
    existing_note, existing_custom_vars = decode_pre_approved_meta(item.note)

    note_to_store = payload.pop("note", existing_note)
    custom_vars_to_store = payload.pop("custom_variables", existing_custom_vars)

    for field, value in payload.items():
        setattr(item, field, value)

    item.note = encode_pre_approved_meta(note_to_store, custom_vars_to_store)

    db.commit()
    db.refresh(item)
    return _to_pre_approved_read(item)


@router.delete("/pre-approved/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pre_approved(item_id: str, current_user: User = Depends(require_owner), db: Session = Depends(get_db)):
    item = db.query(PreApprovedItem).filter(PreApprovedItem.id == item_id, PreApprovedItem.company_id == current_user.company_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pre-approved item not found")
    db.delete(item)
    db.commit()
