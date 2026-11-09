import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
)
from jwt import InvalidTokenError

from app.core.config import settings


password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")

    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(
            minutes=settings.access_token_expire_minutes
        ),
        "type": "access",
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={
                "require": ["sub", "iat", "nbf", "exp", "type"],
            },
        )

        if payload.get("type") != "access":
            raise ValueError("Invalid token type")

        return uuid.UUID(payload["sub"])

    except (
        InvalidTokenError,
        ValueError,
        TypeError,
        KeyError,
    ) as exc:
        raise ValueError("Invalid or expired access token") from exc
