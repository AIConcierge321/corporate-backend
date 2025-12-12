from pydantic import BaseModel, EmailStr
from typing import Optional

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(UserLogin):
    full_name: str
    org_id: Optional[str] = None # In real app, might register org first

class UserResponse(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    
    class Config:
        from_attributes = True

class RefreshRequest(BaseModel):
    refresh_token: str
