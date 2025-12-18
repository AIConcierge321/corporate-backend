from typing import List, Dict, Any
from app.models.booking import Booking, PolicyStatus
from app.models.employee import Employee
from app.schemas.policy import PolicyResult, PolicyViolation

class PolicyEngine:
    """
    Minimal Rule Engine for Phase 5.
    """
    @staticmethod
    def evaluate(booking: Booking, travelers: List[Employee]) -> Dict[str, Any]:
        """
        Evaluate policies against a booking.
        """
        result = PolicyStatus.PASS
        approval_required = False
        violations = []
        
        # Rule 1: High Content Cost (Assume booking field has estimate, or we pass it)
        # For now, rely on booking.total_amount (if set during draft? usually set during search selection)
        # Let's assume draft has 0, but if we had cost...
        
        # Mock Rule: If trip name contains "Luxury", flag it.
        if booking.trip_name and "Luxury" in booking.trip_name:
            result = PolicyStatus.BLOCK
            approval_required = False # Blocked means rejected immediately, no approval path
            violations.append(PolicyViolation(policy="Luxury Travel", severity="hard"))
            
        if booking.trip_name and "Approval Test" in booking.trip_name:
            result = PolicyStatus.WARN
            approval_required = True
            violations.append(PolicyViolation(policy="Manual Approval Test", severity="soft"))
            
        # Mock Rule: If traveler is inactive (shouldn't happen)
        # ...
        
        return {
            "result": result, 
            "approval_required": approval_required, 
            "violations": violations
        }
