from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: str | None = None
    email: str | None = None
    groups: list[str] = []


class SSOCallbackRequest(BaseModel):
    id_token: str  # OIDC ID Token from Okta/Azure/Google
    provider: str


class EmployeeResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    status: str
    external_user_id: str | None = None

    groups: list[str] = []
    permissions: list[str] = []

    class Config:
        from_attributes = True
