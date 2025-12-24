from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.schemas.auth import SSOCallbackRequest, Token, EmployeeResponse
from app.models.employee import Employee
from app.core.config import settings
from app.services import auth_service
from app.api import deps
from app.core.permissions import get_permissions_for_groups
from app.core.rate_limit import limiter
from typing import Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


async def _verify_oidc_token(id_token: str) -> dict:
    """
    Verify OIDC ID token from Identity Provider.
    
    TODO: Implement real OIDC validation when IdP is configured:
    - Fetch JWKS from IdP's /.well-known/openid-configuration
    - Verify token signature
    - Validate issuer, audience, and expiration
    """
    # This is a placeholder for real OIDC implementation
    # When you have IdP credentials, implement proper validation here
    raise NotImplementedError(
        "Real OIDC validation not yet implemented. "
        "Set DEV_MODE=true for local development."
    )


def _dev_mode_mock_auth(id_token: str) -> dict:
    """
    Development-only mock authentication.
    
    NEVER use in production - allows any email to authenticate.
    """
    if not settings.DEV_MODE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OIDC authentication not configured. Contact administrator."
        )
    
    # Log warning for every mock auth
    logger.warning("=" * 50)
    logger.warning("⚠️  MOCK AUTH USED - DEV_MODE is enabled!")
    logger.warning("⚠️  This should NEVER appear in production logs!")
    logger.warning("=" * 50)
    
    # Allow switching user by passing email in id_token for dev/test
    if "@" in id_token:
        email = id_token
    else:
        email = "alice@corporate.com"
    
    return {"email": email, "sub": "dev_mock_" + email}


@router.post("/sso/callback", response_model=Token)
@limiter.limit("5/minute")
async def sso_callback(
    request: Request,
    sso_in: SSOCallbackRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Exchange ID Token from IdP for internal Access Token.
    
    Flow:
    1. Validate ID Token (Signature, Issuer, Aud)
    2. Lookup user by email/external_id in DB (Mirrored via SCIM)
    3. If user exists & active -> Issue internal JWT
    4. If user missing -> Deny (Deny-by-default, SCIM must provision first)
    """
    # Try real OIDC first, fall back to dev mode mock
    try:
        token_payload = await _verify_oidc_token(sso_in.id_token)
        email = token_payload.get("email")
        external_id = token_payload.get("sub")
    except NotImplementedError:
        # Real OIDC not implemented - try dev mode
        mock_payload = _dev_mode_mock_auth(sso_in.id_token)
        email = mock_payload["email"]
        external_id = mock_payload["sub"]
    
    # Check DB for provisioned user
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
@limiter.limit("60/minute")
async def read_users_me(
    request: Request,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Get current user profile with permissions.
    """
    group_names = [g.name for g in current_user.groups]
    permissions = get_permissions_for_groups(group_names)
    
    return EmployeeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        status=current_user.status,
        external_user_id=current_user.external_user_id,
        groups=group_names,
        permissions=list(permissions)
    )

