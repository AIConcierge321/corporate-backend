from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    email: Optional[str] = None
    groups: List[str] = []

class SSOCallbackRequest(BaseModel):
    id_token: str # OIDC ID Token from Okta/Azure/Google
    provider: str

class EmployeeResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: str
    external_user_id: Optional[str] = None
    
    class Config:
        from_attributes = True
