from pydantic import BaseModel
from typing import Optional, List
from app.models.booking import PolicyStatus

class PolicyRequest(BaseModel):
    booking_id: str
    total_amount: Optional[float] = 0

class PolicyViolation(BaseModel):
    policy: str
    severity: str # soft, hard

class PolicyResult(BaseModel):
    result: PolicyStatus
    violations: List[PolicyViolation] = []
    approval_required: bool = False
