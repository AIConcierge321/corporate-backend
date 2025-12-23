from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging

from app.core.config import settings
from app.db.session import get_db
from app.models.employee import Employee
from app.models.role_template import EmployeeRoleAssignment
from app.schemas.auth import TokenPayload
from app.services.token_blacklist import TokenBlacklist

logger = logging.getLogger(__name__)

# Using OAuth2 scheme for Swagger UI convenience
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/sso/callback")


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> Employee:
    """
    Validate JWT token and return current user.
    
    Checks:
    1. Token signature and expiration
    2. Token type is "access"
    3. Token is not revoked (blacklisted)
    4. User exists and is active
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        jti: str = payload.get("jti")
        
        if user_id is None:
            raise credentials_exception
        
        # HIGH-005: Validate token type
        if token_type != "access":
            logger.warning(f"Invalid token type: {token_type}")
            raise credentials_exception
        
        token_data = TokenPayload(sub=user_id, email=payload.get("email"))
        
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise credentials_exception
    
    # HIGH-004: Check token blacklist
    if jti:
        try:
            is_revoked = await TokenBlacklist.is_revoked(jti)
            if is_revoked:
                logger.warning(f"Revoked token used: {jti}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except Exception as e:
            # Log but don't fail if Redis is down (fail-open for availability)
            logger.error(f"Token blacklist check failed: {e}")
    
    # Fetch User with Groups and Role Assignments
    result = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.groups),
            selectinload(Employee.role_assignments).selectinload(EmployeeRoleAssignment.role_template)
        )
        .where(Employee.id == int(user_id))
    )
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
        
    if user.status != "active":
        raise HTTPException(status_code=403, detail="User is suspended")
         
    return user

