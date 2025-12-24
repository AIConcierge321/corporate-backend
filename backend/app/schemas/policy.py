from pydantic import BaseModel

from app.models.booking import PolicyStatus


class PolicyRequest(BaseModel):
    booking_id: str
    total_amount: float | None = 0


class PolicyViolation(BaseModel):
    policy: str
    severity: str  # soft, hard


class PolicyResult(BaseModel):
    result: PolicyStatus
    violations: list[PolicyViolation] = []
    approval_required: bool = False
