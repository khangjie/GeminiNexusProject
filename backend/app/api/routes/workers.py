"""
Workers routes — owner can invite workers to the company by Gmail address.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_owner
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/workers", tags=["workers"])


class InviteWorkerRequest(BaseModel):
    email: EmailStr
    name: str = ""


@router.get("/", response_model=list[UserRead])
def list_workers(current_user: User = Depends(require_owner), db: Session = Depends(get_db)):
    """List all workers belonging to the owner's company."""
    return (
        db.query(User)
        .filter(User.company_id == current_user.company_id, User.role == "worker")
        .all()
    )


@router.post("/invite", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def invite_worker(body: InviteWorkerRequest, current_user: User = Depends(require_owner), db: Session = Depends(get_db)):
    """
    Add a worker to the company by their Gmail address.
    If the user already exists, assign them to this company.
    If not, create a pending account; they will complete sign-up via Firebase Auth.
    """
    if not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner is not assigned to a company")

    existing = db.query(User).filter(User.email == str(body.email)).first()
    if existing:
        if existing.company_id and existing.company_id != current_user.company_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already belongs to another company")
        existing.company_id = current_user.company_id
        existing.role = "worker"
        db.commit()
        db.refresh(existing)
        return existing

    # Create a placeholder account; activated when the worker signs in with Firebase
    worker = User(
        email=str(body.email),
        name=body.name or str(body.email).split("@")[0],
        role="worker",
        company_id=current_user.company_id,
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


@router.delete("/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_worker(worker_id: str, current_user: User = Depends(require_owner), db: Session = Depends(get_db)):
    worker = db.query(User).filter(
        User.id == worker_id, User.company_id == current_user.company_id, User.role == "worker"
    ).first()
    if not worker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    worker.company_id = None
    db.commit()
