from typing import Any

from pydantic import BaseModel, Field


class SCIMName(BaseModel):
    givenName: str
    familyName: str
    formatted: str | None = None


class SCIMEmail(BaseModel):
    value: str
    type: str = "work"
    primary: bool = True


class SCIMManager(BaseModel):
    value: str
    displayName: str | None = None


class SCIMEnterpriseExtension(BaseModel):
    manager: SCIMManager | None = None
    department: str | None = None
    costCenter: str | None = None
    division: str | None = None


class SCIMUserCreate(BaseModel):
    schemas: list[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    userName: str
    name: SCIMName
    emails: list[SCIMEmail]
    mid: str | None = None  # External ID
    active: bool = True
    title: str | None = None  # Job Title
    phoneNumbers: list[dict[str, str]] | None = None

    # Map the enterprise extension using alias
    enterprise_extension: SCIMEnterpriseExtension | None = Field(
        None, validation_alias="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )


class SCIMUserResponse(SCIMUserCreate):
    id: str
    meta: Any = None
