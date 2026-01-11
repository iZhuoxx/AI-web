"""Security helpers for password hashing, JWT sessions, and CSRF signing."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from itsdangerous import BadSignature, URLSafeTimedSerializer
from jose import JWTError, jwt
from passlib.context import CryptContext

from api.settings import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Shared signer for time-bound CSRF tokens (double-submit cookie pattern).
csrf_serializer = URLSafeTimedSerializer(settings.CSRF_SECRET, salt="csrf-token")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    # Standard JWT claims: subject, expiration, issued-at.
    to_encode: Dict[str, Any] = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as exc:  # pragma: no cover - normalize jose errors for callers
        raise ValueError("Invalid token") from exc


def generate_csrf_token() -> str:
    token = secrets.token_urlsafe(32)
    return csrf_serializer.dumps({"token": token})


def verify_csrf_token(token: str) -> bool:
    try:
        csrf_serializer.loads(token, max_age=settings.CSRF_TOKEN_TTL_SECONDS)
        return True
    except BadSignature:
        return False
