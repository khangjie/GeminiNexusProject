"""
Auth routes — Firebase ID token verification + JWT issuance.
The frontend sends the Firebase ID token after Google Sign-In.
We verify it, upsert the user record, and return our own JWT.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import _repair_owner_company_association
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.user import TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class FirebaseTokenRequest(BaseModel):
    firebase_id_token: str
    role: str = "worker"  # "owner" | "worker"
    name: Optional[str] = None


class DevLoginRequest(BaseModel):
    email: str
    role: str = "worker"  # "owner" | "worker"
    name: Optional[str] = None
    company_id: Optional[str] = None


class AdminUserRead(UserRead):
    owned_company_id: Optional[str] = None
    receipt_count: int = 0


def _issue_jwt(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _verify_firebase_token(id_token: str) -> dict:
    """
    Verify Firebase ID token using google-auth library.
    Returns decoded claims dict with 'uid', 'email', 'name'.
    """
    try:
        import google.auth.transport.requests
        import google.oauth2.id_token

        request = google.auth.transport.requests.Request()
        claims = google.oauth2.id_token.verify_firebase_token(id_token, request, audience=settings.FIREBASE_PROJECT_ID)
        return claims
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Firebase token invalid: {exc}")


def _require_dev_admin(
    admin_username: Optional[str] = Header(default=None, alias="X-Admin-Username"),
    admin_password: Optional[str] = Header(default=None, alias="X-Admin-Password"),
):
    if not settings.ENABLE_DEV_AUTH:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dev admin disabled")
    if admin_username != "admin" or admin_password != "Admin@123":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credential")


@router.get("/dev-admin/users", response_model=list[AdminUserRead])
def list_dev_admin_users(_: None = Depends(_require_dev_admin), db: Session = Depends(get_db)):
    from app.models.company import Company
    from app.models.receipt import Receipt

    users = db.query(User).order_by(User.created_at.desc()).all()
    result: list[AdminUserRead] = []
    for user in users:
        owned_company = db.query(Company).filter(Company.owner_id == user.id).first()
        receipt_count = db.query(Receipt).filter(Receipt.worker_id == user.id).count()
        result.append(
            AdminUserRead(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                company_id=user.company_id,
                created_at=user.created_at,
                owned_company_id=owned_company.id if owned_company else None,
                receipt_count=receipt_count,
            )
        )
    return result


@router.delete("/dev-admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dev_admin_user(user_id: str, _: None = Depends(_require_dev_admin), db: Session = Depends(get_db)):
    from app.models.company import Company
    from app.models.receipt import Receipt

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    owned_company = db.query(Company).filter(Company.owner_id == user.id).first()
    if owned_company:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete owner while they still own a company",
        )

    receipt_count = db.query(Receipt).filter(Receipt.worker_id == user.id).count()
    if receipt_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete user while receipts still reference them",
        )

    db.delete(user)
    db.commit()


@router.post("/login", response_model=TokenResponse)
def login(body: FirebaseTokenRequest, db: Session = Depends(get_db)):
    """Exchange a Firebase ID token for an app-level JWT."""
    claims = _verify_firebase_token(body.firebase_id_token)

    google_uid: str = claims["uid"]
    email: str = claims.get("email", "")
    name: str = body.name or claims.get("name", email.split("@")[0])

    user = db.query(User).filter(User.google_uid == google_uid).first()
    if not user:
        # New user — create record
        user = User(email=email, name=name, role=body.role, google_uid=google_uid)
        db.add(user)
        db.commit()
        db.refresh(user)

    user = _repair_owner_company_association(user, db)

    token = _issue_jwt(user.id)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/dev-login", response_model=TokenResponse)
def dev_login(body: DevLoginRequest, db: Session = Depends(get_db)):
    """Local development auth bypass (disabled unless ENABLE_DEV_AUTH=true)."""
    if not settings.ENABLE_DEV_AUTH:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dev login disabled")

    role = body.role if body.role in ("owner", "worker") else "worker"
    name = body.name or body.email.split("@")[0]
    google_uid = f"dev:{body.email.lower()}"

    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        user = User(
            email=body.email,
            name=name,
            role=role,
            google_uid=google_uid,
            company_id=body.company_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.name = name
        user.role = role
        if body.company_id is not None:
            user.company_id = body.company_id
        if not user.google_uid:
            user.google_uid = google_uid
        db.commit()
        db.refresh(user)

    user = _repair_owner_company_association(user, db)

    token = _issue_jwt(user.id)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user
