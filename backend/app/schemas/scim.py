from pydantic import BaseModel, Field
from typing import List, Optional, Any

class SCIMName(BaseModel):
    givenName: str
    familyName: str
    formatted: Optional[str] = None

class SCIMEmail(BaseModel):
    value: str
    type: str = "work"
    primary: bool = True

class SCIMManager(BaseModel):
    value: str
    displayName: Optional[str] = None

class SCIMEnterpriseExtension(BaseModel):
    manager: Optional[SCIMManager] = None
    department: Optional[str] = None

class SCIMUserCreate(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    userName: str
    name: SCIMName
    emails: List[SCIMEmail]
    mid: Optional[str] = None # External ID
    active: bool = True
    
    # Map the enterprise extension using alias
    enterprise_extension: Optional[SCIMEnterpriseExtension] = Field(
        None, 
        validation_alias="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )

class SCIMUserResponse(SCIMUserCreate):
    id: str
    meta: Any = None
