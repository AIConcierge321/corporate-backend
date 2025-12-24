from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, PolicyStatus
from app.models.employee import Employee
from app.models.organization import ApprovalMode, Organization
from app.schemas.policy import PolicyViolation


class PolicyEngine:
    """
    Advanced Rule Engine implementing:
    - Always Ask vs Only When Necessary
    - Cost Controls
    - Advance Booking rules
    - Class Eligibility (Hierarchy Based)
    """

    @staticmethod
    async def evaluate(
        db: AsyncSession, booking: Booking, travelers: list[Employee]
    ) -> dict[str, Any]:
        """
        Evaluate policies against a booking.
        """
        # 1. Fetch Organization Policy Settings
        stmt = select(Organization).where(Organization.id == booking.org_id)
        result = await db.execute(stmt)
        org = result.scalars().first()

        if not org:
            # Fallback safe default
            return {"result": PolicyStatus.PASS, "approval_required": True, "violations": []}

        settings = org.policy_settings or {}
        mode = org.approval_mode or ApprovalMode.ALWAYS_ASK

        violations = []
        hard_block = False

        # --- 2. Cost Controls ---
        # Rule: Max airfare/total cost
        # Defaults to $1000 if not set
        max_amount = settings.get("max_amount", 1000.0)
        if booking.total_amount and booking.total_amount > max_amount:
            violations.append(
                PolicyViolation(
                    policy="Max Cost Exceeded",
                    severity="hard",
                    details=f"Amount {booking.total_amount} > Limit {max_amount}",
                )
            )

        # --- 3. Advance Booking Rules ---
        # Rule: Minimum days in advance
        min_days = settings.get("min_advance_days", 7)
        if booking.start_date:
            # Ensure timezone awareness
            now = datetime.now(UTC)
            start = booking.start_date
            if start.tzinfo is None:
                start = start.replace(tzinfo=UTC)

            delta = (start - now).days
            if delta < min_days:
                violations.append(
                    PolicyViolation(
                        policy="Advance Booking Violation",
                        severity="soft",
                        details=f"Booked {delta} days ahead, required {min_days}",
                    )
                )

        # --- 4. Travel Class Eligibility ---
        # Example: Business Class -> CEO/C-Suite only
        # We need a way to identify "C-Suite". For now, we check Job Title or Grade?
        # Let's use a simple Title check from settings
        allowed_business_titles = settings.get(
            "business_class_titles", ["CEO", "CTO", "CFO", "Director"]
        )

        if booking.travel_class and booking.travel_class.lower() in {"business", "first"}:
            # Check if ALL travelers are eligible? Or ANY?
            # Typically, if a VIP travels, entourage might get upgrade, but let's be strict: ALL must be eligible.
            for t in travelers:
                title = t.job_title or ""
                # Simple iterator check
                is_eligible = any(allowed in title for allowed in allowed_business_titles)
                if not is_eligible:
                    violations.append(
                        PolicyViolation(
                            policy="Travel Class Violation",
                            severity="soft",  # Usually requires approval, not hard block
                            details=f"Traveler {t.full_name} ({title}) not eligible for {booking.travel_class}",
                        )
                    )

        # --- 5. Determine Final Status ---

        # Check for HARD BLOCKS (e.g. if we had a "Denied Destination" list)
        if hard_block:
            return {
                "result": PolicyStatus.BLOCK,
                "approval_required": False,
                "violations": violations,
            }

        # Approval Logic
        approval_required = False

        if mode == ApprovalMode.ALWAYS_ASK:
            approval_required = True
        elif mode == ApprovalMode.ONLY_WHEN_NECESSARY:
            approval_required = len(violations) > 0

        # Result Status
        final_status = PolicyStatus.PASS
        if violations:
            final_status = PolicyStatus.WARN  # Default to WARN so manager can override

        return {
            "result": final_status,
            "approval_required": approval_required,
            "violations": violations,
        }
