from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.schemas.auth import SSOCallbackRequest, Token, EmployeeResponse
from app.models.employee import Employee
from app.core import config
from app.services import auth_service
from app.api import deps
from typing import Any

router = APIRouter()

@router.post("/sso/callback", response_model=Token)
async def sso_callback(
    sso_in: SSOCallbackRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Exchange ID Token from IdP for internal Access Token.
    1. Validate ID Token (Signature, Issuer, Aud) - Mocked for now.
    2. Lookup user by email/external_id in DB (Mirrored via SCIM).
    3. If user exists & active -> Issue internal JWT.
    4. If user missing -> Deny (Deny-by-default, SCIM must provision first).
    """
    # TODO: Real OIDC Validation
    # payload = verify_oidc_token(sso_in.id_token)
    
    # Mock Validation
    email = "alice@corporate.com" # Extract from token
    external_id = "okta_123"   # Extract from token
    
    # Check DB
    result = await db.execute(select(Employee).where(Employee.email == email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=401, 
            detail="User not provisioned. Please contact IT."
        )
        
    if user.status != "active":
        raise HTTPException(status_code=403, detail="User is suspended")

    # Issue Internal Token
    access_token = auth_service.create_internal_token(user)
    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=EmployeeResponse)
async def read_users_me(
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Get current user profile (synced from IdP).
    """
    return current_user
