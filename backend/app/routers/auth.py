from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import User
from app.schemas import TokenOut, UserLogin, UserOut, UserProfileUpdate, UserRegister
from app.workspace import accept_pending_invitations, create_workspace, ensure_user_workspace

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email or user.username,
        display_name=user.display_name or "",
        is_admin=user.is_admin,
        active_workspace_id=user.active_workspace_id,
        created_at=user.created_at,
    )


def _find_user_by_email(db: Session, email: str) -> User | None:
    normalized = _normalize_email(email)
    return (
        db.query(User)
        .filter(or_(User.email == normalized, User.username == normalized))
        .first()
    )


@router.post("/register", response_model=TokenOut)
def register(payload: UserRegister, db: Annotated[Session, Depends(get_db)]) -> TokenOut:
    email = _normalize_email(payload.email)
    if _find_user_by_email(db, email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        username=email,
        email=email,
        display_name="",
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    accept_pending_invitations(db, user)
    if user.active_workspace_id is None:
        label = email.split("@")[0]
        create_workspace(db, owner=user, name=f"{label} 的团队")
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, email)
    return TokenOut(access_token=token, user=_user_out(user))


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Annotated[Session, Depends(get_db)]) -> TokenOut:
    user = _find_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    accept_pending_invitations(db, user)
    ensure_user_workspace(db, user)
    db.commit()
    db.refresh(user)
    email = user.email or user.username
    token = create_access_token(user.id, email)
    return TokenOut(access_token=token, user=_user_out(user))


@router.get("/me", response_model=UserOut)
def me(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserOut:
    ensure_user_workspace(db, current_user)
    db.commit()
    db.refresh(current_user)
    return _user_out(current_user)


@router.put("/profile", response_model=UserOut)
def update_profile(
    payload: UserProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserOut:
    current_user.display_name = payload.display_name.strip()
    db.commit()
    db.refresh(current_user)
    return _user_out(current_user)
