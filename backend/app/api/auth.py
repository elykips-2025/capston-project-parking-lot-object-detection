from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

DbSession = Annotated[Session, Depends(get_db)]

# Used to perform password verification for unknown accounts.
# This hash is not associated with a real user.
DUMMY_PASSWORD_HASH = hash_password(
    "ParkSight-Nonexistent-Account-Verification"
)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: DbSession,
):
    email = payload.email.strip().lower()

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = db.scalar(
        select(User).where(User.email == email)
    )

    password_hash = (
        user.password_hash
        if user is not None
        else DUMMY_PASSWORD_HASH
    )

    password_valid = verify_password(
        payload.password,
        password_hash,
    )

    if user is None or not password_valid or not user.is_active:
        raise invalid_credentials

    return TokenResponse(
        access_token=create_access_token(user.id),
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )
