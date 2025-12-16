from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.booking import Booking, BookingStatus, PolicyStatus
from app.models.employee import Employee
from app.models.approval import ApprovalRequest, ApprovalStatus

class BookingStateMachine:
    """
    Manages booking lifecycle transitions.
    Prevent direct manipulation of booking.status outside this service.
    """
    
    @staticmethod
    async def submit_draft(db: AsyncSession, booking: Booking, policy_result: dict) -> Booking:
        """
        Transition from DRAFT -> POLICY_EVALUATED -> (APPROVED/PENDING)
        """
        if booking.status != BookingStatus.DRAFT:
             raise HTTPException(status_code=400, detail="Only draft bookings can be submitted.")
        
        # Apply Policy Result
        # policy_result input example: {'result': 'warn', 'approval_required': True}
        
        p_status = policy_result.get("result", PolicyStatus.PASS)
        approval_req = policy_result.get("approval_required", False)
        
        booking.policy_status = p_status
        booking.approval_required = approval_req
        
        if p_status == PolicyStatus.BLOCK:
            booking.status = BookingStatus.REJECTED
            # TODO: Add violation reason to local db or response
            msg = "Booking blocked by policy."
            raise HTTPException(status_code=400, detail=msg)
            
        booking.status = BookingStatus.POLICY_EVALUATED
        
        # Auto-transition based on approval
        if approval_req:
            # 1. Routing Logic: Find Manager
            # We need to fetch the booker to find their manager
            # Use explicit query to be safe with async session
            from sqlalchemy import select
            stmt = select(Employee).where(Employee.id == booking.booker_id)
            result = await db.execute(stmt)
            booker = result.scalars().first()
            
            if not booker or not booker.manager_id:
                # TODO: Fallback to Org Admin or specific group?
                # For now, we require a manager.
                raise HTTPException(status_code=400, detail="Approval required but no manager assigned to user.")
            
            # 2. Create Approval Request
            from app.models.approval import ApprovalRequest, ApprovalStatus
            req = ApprovalRequest(
                booking_id=booking.id,
                approver_id=booker.manager_id,
                status=ApprovalStatus.PENDING
            )
            db.add(req)
            
            booking.status = BookingStatus.PENDING_APPROVAL
            # TODO: Trigger approval notification
        else:
             booking.status = BookingStatus.APPROVED
             # Ready for booking/ticketing
             
        await db.commit()
        await db.refresh(booking)
        return booking

    @staticmethod
    async def approve_booking(db: AsyncSession, booking: Booking, approver: Employee) -> Booking:
        """
        Transition PENDING_APPROVAL -> APPROVED
        """
        if booking.status != BookingStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=400, detail="Booking is not pending approval.")
            
        # TODO: Verify approver permissions (e.g., is manager of booker?)
        
        booking.status = BookingStatus.APPROVED
        await db.commit()
        await db.refresh(booking)
        return booking
        
    @staticmethod
    async def reject_booking(db: AsyncSession, booking: Booking, approver: Employee) -> Booking:
         if booking.status != BookingStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=400, detail="Booking is not pending approval.")
         
         booking.status = BookingStatus.REJECTED
         await db.commit()
         await db.refresh(booking)
         return booking
