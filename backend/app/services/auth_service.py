from datetime import datetime, timedelta
from typing import Union, Any
from jose import jwt
from app.core.config import settings
from app.models.employee import Employee

def create_internal_token(user: Employee, expires_delta: timedelta = None) -> str:
    """
    Generate short-lived internal JWT for API access.
    Subject is the user's Internal ID.
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # We embed org_id and status in token for quick middleware checks
    to_encode = {
        "exp": expire, 
        "sub": str(user.id), 
        "email": user.email,
        "org_id": str(user.org_id),
        "type": "access"
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
