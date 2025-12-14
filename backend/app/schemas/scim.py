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

class SCIMUserCreate(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    userName: str
    name: SCIMName
    emails: List[SCIMEmail]
    mid: Optional[str] = None # External ID
    active: bool = True

class SCIMUserResponse(SCIMUserCreate):
    id: str
    meta: Any = None
