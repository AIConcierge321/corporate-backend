from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from jose import jwt, JWTError
from app.core import security
from app.core.config import settings
from app.models.employee import Employee
from app.models.organization import Organization
from app.schemas.auth import UserCreate, UserLogin, Token
from app.services.redis_client import RedisService

async def authenticate_user(db: AsyncSession, email: str, password: str) -> Employee | None:
    result = await db.execute(select(Employee).where(Employee.email == email))
    user = result.scalars().first()
    if not user:
        return None
    if not security.verify_password(password, user.hashed_password):
        return None
    return user

async def register_user_db(db: AsyncSession, user_in: UserCreate) -> Employee:
    # Check if user exists
    result = await db.execute(select(Employee).where(Employee.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    # Create default org if not provided (for quick start)
    # In real world, we might require org_id or create a new org
    if not user_in.org_id:
        # Check if any org exists, or create one "Default Org"
        result = await db.execute(select(Organization))
        org = result.scalars().first()
        if not org:
            org = Organization(name="Default Organization")
            db.add(org)
            await db.flush()
        org_id = org.id
    else:
        org_id = user_in.org_id

    # Create user
    db_user = Employee(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        org_id=org_id,
        role="admin" # First user as admin for simplicity
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def create_tokens(user_id: int) -> Token:
    access_token = security.create_access_token(user_id)
    refresh_token = security.create_refresh_token(user_id)
    return Token(
        access_token=access_token, 
        refresh_token=refresh_token, 
        token_type="bearer"
    )

async def blacklist_token(token: str):
    # Decode token to get expiration
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp = payload.get("exp")
        # Calculate TTL
        # Simple approach: just use standard refresh expiry or access expiry
        redis = RedisService.get_client()
        await redis.setex(f"blacklist:{token}", settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, "true")
    except Exception as e:
        print(f"Error blacklisting token: {e}")
        pass

async def is_token_blacklisted(token: str) -> bool:
    redis = RedisService.get_client()
    exists = await redis.get(f"blacklist:{token}")
    return exists is not None
