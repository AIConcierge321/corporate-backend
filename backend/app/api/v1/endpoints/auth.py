from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services import auth_service
from app.schemas.auth import Token, UserCreate, UserResponse, RefreshRequest
from app.core import security
from app.core.config import settings
from app.api import deps
from jose import jwt, JWTError

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Register a new user.
    """
    user = await auth_service.register_user_db(db, user_in)
    return user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = await auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return await auth_service.create_tokens(user.id)

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_in: RefreshRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get new access token using refresh token.
    """
    try:
        payload = jwt.decode(
            refresh_in.refresh_token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        
        user_id = payload.get("sub")
        # Check blacklist
        if await auth_service.is_token_blacklisted(refresh_in.refresh_token):
             raise HTTPException(status_code=400, detail="Token revoked")
             
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")

    return await auth_service.create_tokens(user_id)

@router.post("/logout")
async def logout(
    token: str = Depends(deps.oauth2_scheme),
    refresh_in: RefreshRequest = None
):
    """
    Logout user (blacklist tokens).
    Pass access token in Header, and optionally refresh token in body to blacklist both.
    """
    await auth_service.blacklist_token(token)
    if refresh_in:
        await auth_service.blacklist_token(refresh_in.refresh_token)
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user
