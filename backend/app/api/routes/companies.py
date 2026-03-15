"""
Company routes — create, list, and retrieve companies.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_owner
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyRead

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/", response_model=list[CompanyRead])
def list_companies(db: Session = Depends(get_db)):
    """List all companies (used for 'View Other Company' dropdown)."""
    return db.query(Company).all()


@router.post("/", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(body: CompanyCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    company = Company(name=body.name, owner_id=current_user.id)
    db.add(company)
    db.flush()
    # Assign owner to this company
    current_user.company_id = company.id
    db.commit()
    db.refresh(company)
    return company


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company
