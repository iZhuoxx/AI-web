"""Authentication and session management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, require_csrf
from api.db.database import get_db
from api.db import models
from api.schemas import MembershipOut, SessionInfo, UserCreate, UserLogin, UserOut
from api.security import create_access_token, generate_csrf_token, hash_password, verify_password
from api.settings import settings


router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=True,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=True,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )


def _set_csrf_cookie(response: Response) -> str:
    token = generate_csrf_token()
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=token,
        max_age=settings.CSRF_TOKEN_TTL_SECONDS,
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=False,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )
    return token


def _membership_to_schema(m: models.Membership) -> MembershipOut:
    return MembershipOut(
        id=str(m.id),
        plan=m.plan,
        status=m.status.value,
        started_at=m.started_at,
        ends_at=m.ends_at,
    )


def _user_to_schema(user: models.User) -> UserOut:
    return UserOut.from_orm(user)


def _session_info(user: models.User, db: Session) -> SessionInfo:
    memberships = (
        db.execute(
            select(models.Membership)
            .where(models.Membership.user_id == user.id)
            .order_by(models.Membership.started_at.desc())
        )
        .scalars()
        .all()
    )
    return SessionInfo(
        user=_user_to_schema(user),
        memberships=[_membership_to_schema(m) for m in memberships],
    )


@router.get('/csrf')
def get_csrf_token(response: Response) -> dict[str, str]:
    token = _set_csrf_cookie(response)
    return {"csrf_token": token}


@router.post("/register", response_model=SessionInfo, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
def register_user(payload: UserCreate, response: Response, db: Session = Depends(get_db)) -> SessionInfo:
    existing = db.execute(select(models.User).where(models.User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = models.User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    _set_session_cookie(response, token)
    _set_csrf_cookie(response)
    return _session_info(user, db)


@router.post("/login", response_model=SessionInfo, dependencies=[Depends(require_csrf)])
def login_user(payload: UserLogin, response: Response, db: Session = Depends(get_db)) -> SessionInfo:
    user = db.execute(select(models.User).where(models.User.email == payload.email)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    token = create_access_token(str(user.id))
    _set_session_cookie(response, token)
    _set_csrf_cookie(response)
    return _session_info(user, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
def logout_user(response: Response) -> Response:
    _clear_session_cookie(response)
    _set_csrf_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=SessionInfo)
def get_current_session(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> SessionInfo:
    return _session_info(user, db)
