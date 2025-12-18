from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.schemas.scim import SCIMUserCreate, SCIMUserResponse
from app.models.employee import Employee
from app.models.organization import Organization
from typing import Any

router = APIRouter()

async def validate_scim_token(authorization: str = Header(None)):
    """
    Validate Bearer token from IdP.
    In real world, this matches a long-lived 'SCIM Token' generated for the Org.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing SCIM Token")
    # TODO: Lookup Org by Token
    return True

@router.post("/Users", status_code=201)
async def create_scim_user(
    user_in: SCIMUserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorized: bool = Depends(validate_scim_token)
) -> Any:
    """
    SCIM v2 Create User
    """
    # 1. Find Org (Hardcoded for single-tenant dev for now)
    result = await db.execute(select(Organization))
    org = result.scalars().first()
    if not org:
        # Create default org if missing
        org = Organization(name="Default Org")
        db.add(org)
        await db.flush()
    
    # 2. Check overlap
    email = user_in.emails[0].value
    result = await db.execute(select(Employee).where(Employee.email == email))
    existing = result.scalars().first()
    
    if existing:
        # SCIM requires 409 Conflict if exists
        raise HTTPException(status_code=409, detail="User already exists")
        
    # 3. Create
    new_user = Employee(
        email=email,
        external_user_id=user_in.userName, # Or externalId field
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
    
    # 4. Return SCIM Response
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
