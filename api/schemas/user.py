"""Pydantic models for user-related payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: Optional[str] = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class MembershipOut(BaseModel):
    id: UUID
    plan: str
    status: str
    started_at: datetime
    ends_at: Optional[datetime]


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    name: Optional[str]
    is_active: bool
    member_plan: Optional[str]
    member_until: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class SessionInfo(BaseModel):
    user: UserOut
    memberships: list[MembershipOut] = Field(default_factory=list)
