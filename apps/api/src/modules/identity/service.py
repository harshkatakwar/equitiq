"""Identity module — Authentication service."""

from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.modules.identity.models import User

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: uuid.UUID) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours)
    payload = {
        "sub": str(user_id),
        "exp": expires,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, password: str, display_name: str | None = None, role: str = "user") -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user
