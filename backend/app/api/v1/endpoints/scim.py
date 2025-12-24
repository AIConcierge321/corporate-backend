from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from app.db.session import get_db
from app.schemas.scim import SCIMUserCreate, SCIMUserResponse
from app.models.employee import Employee
from app.models.organization import Organization
from app.models.scim_token import ScimToken
from app.core.config import settings
from app.core.rate_limit import limiter
from typing import Any, Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


async def validate_scim_token(
    authorization: str = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db)
) -> Organization:
    """
    Validate Bearer token from IdP and return associated organization.
    
    Token format: "Bearer <token>"
    """
    if not authorization:
        logger.warning("SCIM request without Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Missing Authorization header"
        )
    
    # Parse Bearer token
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <token>"
        )
    
    raw_token = parts[1]
    
    # DEV_MODE: Allow a special dev token for local testing
    if settings.DEV_MODE and raw_token == "dev-scim-token":
        logger.warning("⚠️ DEV_MODE: Using development SCIM token!")
        # Return first org for dev mode
        result = await db.execute(select(Organization))
        org = result.scalars().first()
        if org:
            return org
        # Create default org if none exists in dev mode
        org = Organization(name="Default Org (Dev)")
        db.add(org)
        await db.flush()
        return org
    
    # Production: Validate token against database
    token_hash = ScimToken.hash_token(raw_token)
    
    stmt = select(ScimToken).options(
        selectinload(ScimToken.organization)
    ).where(
        ScimToken.token_hash == token_hash,
        ScimToken.is_active == True
    )
    result = await db.execute(stmt)
    scim_token = result.scalars().first()
    
    if not scim_token:
        logger.warning(f"Invalid SCIM token attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired SCIM token"
        )
    
    # Update last used timestamp
    scim_token.last_used_at = datetime.now(timezone.utc)
    
    logger.info(f"SCIM token validated for org: {scim_token.organization.name}")
    return scim_token.organization


@router.post("/Users", status_code=201)
@limiter.limit("100/hour")
async def create_scim_user(
    user_in: SCIMUserCreate,
    request: Request,
    org: Organization = Depends(validate_scim_token),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    SCIM v2 Create User
    
    Token must be valid and associated with an organization.
    """
    # HIGH-001: Validate emails list exists and is not empty
    if not user_in.emails or len(user_in.emails) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one email is required"
        )
    
    email = user_in.emails[0].value
    
    # Validate email format
    from email_validator import validate_email, EmailNotValidError
    try:
        # This validates format and normalizes the email
        validated = validate_email(email)
        email = validated.email
    except EmailNotValidError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid email format: {str(e)}"
        )
    
    # Validate required name fields
    if not user_in.name:
        raise HTTPException(
            status_code=400,
            detail="Name object is required"
        )
    
    if not user_in.name.givenName or not user_in.name.familyName:
        raise HTTPException(
            status_code=400,
            detail="Given name and family name are required"
        )
    
    # Check for existing user
    result = await db.execute(select(Employee).where(Employee.email == email))
    existing = result.scalars().first()
    
    if existing:
        # SCIM requires 409 Conflict if exists
        raise HTTPException(status_code=409, detail="User already exists")
        
    # Create user scoped to the authenticated organization
    new_user = Employee(
        email=email,
        external_user_id=user_in.userName,
        first_name=user_in.name.givenName,
        last_name=user_in.name.familyName,
        full_name=f"{user_in.name.givenName} {user_in.name.familyName}",
        org_id=org.id,
        status="active" if user_in.active else "suspended",
        is_active=user_in.active,
        job_title=user_in.title,
        department=user_in.enterprise_extension.department if user_in.enterprise_extension else None,
        cost_center=user_in.enterprise_extension.costCenter if user_in.enterprise_extension else None,
        division=user_in.enterprise_extension.division if user_in.enterprise_extension else None,
        phone_number=user_in.phoneNumbers[0]["value"] if user_in.phoneNumbers and len(user_in.phoneNumbers) > 0 else None
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    logger.info(f"SCIM: Created user {email} for org {org.name}")
    
    # Return SCIM Response
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": str(new_user.id),
        "userName": new_user.email,
        "active": new_user.is_active,
        "emails": [{"value": new_user.email, "primary": True}],
        "meta": {
            "resourceType": "User",
            "created": new_user.created_at.isoformat(),
            "location": str(request.url)
        }
    }

