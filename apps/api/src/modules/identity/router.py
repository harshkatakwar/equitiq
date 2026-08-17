"""Identity module — Auth API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.config import get_settings
from src.modules.identity.schemas import UserRegister, UserLogin, UserResponse, TokenResponse
from src.modules.identity.service import (
    authenticate_user, create_user, get_user_by_email, create_access_token,
)
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.models import User

router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await create_user(db, body.email, body.password, body.display_name)
    await db.commit()
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/demo-login", response_model=TokenResponse)
async def demo_login(db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, settings.demo_user_email)
    if not user:
        # Create demo user on first login
        user = await create_user(
            db, settings.demo_user_email, settings.demo_user_password,
            display_name="Demo User", role="user"
        )
        await db.commit()
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/logout")
async def logout():
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)
