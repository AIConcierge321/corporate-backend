from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.auth import TokenPayload

# Using OAuth2 scheme for Swagger UI convenience, though flow is SSO
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/sso/callback")  

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> Employee:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenPayload(sub=user_id, email=payload.get("email"))
    except JWTError:
        raise credentials_exception
    
    # Fetch User with Groups
    result = await db.execute(
        select(Employee)
        .options(selectinload(Employee.groups))
        .where(Employee.id == int(user_id))
    )
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
        
    if user.status != "active":
         raise HTTPException(status_code=403, detail="User is suspended")
         
    return user
