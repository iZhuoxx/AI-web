"""FastAPI dependencies for session authentication and CSRF checks."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.db import models
from api.security import decode_token, verify_csrf_token
from api.settings import settings


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> models.User | None:
    """Resolve the current user from the session cookie, or return None."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    try:
        # Session subjects are UUIDs in this app.
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        return None
    user = db.get(models.User, uid)
    if not user or not user.is_active:
        return None
    return user


def get_current_user(user: models.User | None = Depends(get_optional_user)) -> models.User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_csrf(request: Request) -> None:
    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    header_token = request.headers.get(settings.CSRF_HEADER_NAME)
    if not cookie_token or not header_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF token")
    # Double-submit cookie: header must match cookie value.
    if cookie_token != header_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token mismatch")
    if not verify_csrf_token(cookie_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
