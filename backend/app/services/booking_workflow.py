from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.models.booking import Booking, BookingStatus, PolicyStatus
from app.models.employee import Employee
from app.models.approval import ApprovalRequest, ApprovalStatus
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService

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
        p_status = policy_result.get("result", PolicyStatus.PASS)
        approval_req = policy_result.get("approval_required", False)
        
        booking.policy_status = p_status
        booking.approval_required = approval_req
        
        if p_status == PolicyStatus.BLOCK:
            booking.status = BookingStatus.REJECTED
            msg = "Booking blocked by policy."
            raise HTTPException(status_code=400, detail=msg)
            
        booking.status = BookingStatus.POLICY_EVALUATED
        
        # Auto-transition based on approval
        if approval_req:
            # 1. Routing Logic: Find Manager
            stmt = select(Employee).where(Employee.id == booking.booker_id)
            result = await db.execute(stmt)
            booker = result.scalars().first()
            
            if not booker or not booker.manager_id:
                raise HTTPException(status_code=400, detail="Approval required but no manager assigned to user.")
            
            # Fetch Manager Email for notification
            stmt_mgr = select(Employee).where(Employee.id == booker.manager_id)
            res_mgr = await db.execute(stmt_mgr)
            manager = res_mgr.scalars().first()

            # 2. Create Approval Request
            req = ApprovalRequest(
                booking_id=booking.id,
                approver_id=booker.manager_id,
                status=ApprovalStatus.PENDING
            )
            db.add(req)
            
            # Audit & Notify
            booking.status = BookingStatus.PENDING_APPROVAL
            
            AuditService.log(
                db, "booking", booking.id, booking.booker_id, "SUBMIT", 
                from_state="draft", to_state="pending_approval", 
                details=jsonable_encoder(policy_result)
            )
            
            if manager:
                await NotificationService.send_email(
                    manager.email, 
                    f"Approval Required: {booking.trip_name}", 
                    f"Please approve booking {booking.id} for {booker.full_name}"
                )

        else:
             booking.status = BookingStatus.APPROVED
             
             AuditService.log(
                db, "booking", booking.id, booking.booker_id, "SUBMIT_AUTO_APPROVE", 
                from_state="draft", to_state="approved", 
                details=jsonable_encoder(policy_result)
             )
             
             # Notify Booker
             # Ensure booker is loaded
             stmt = select(Employee).where(Employee.id == booking.booker_id)
             result = await db.execute(stmt)
             booker = result.scalars().first()
                 
             if booker:
                await NotificationService.send_email(
                    booker.email,
                    f"Booking Approved: {booking.trip_name}",
                    "Your booking has been auto-approved."
                )

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
            
        old_status = booking.status
        booking.status = BookingStatus.APPROVED

        AuditService.log(
            db, "booking", booking.id, approver.id, "APPROVE", 
            from_state=str(old_status.value), to_state=str(BookingStatus.APPROVED.value)
        )
        
        # Notify Booker
        stmt = select(Employee).where(Employee.id == booking.booker_id)
        result = await db.execute(stmt)
        booker = result.scalars().first()
        
        if booker:
            await NotificationService.send_email(
                booker.email,
                f"Booking Approved: {booking.trip_name}",
                f"Your booking was approved by {approver.full_name}."
            )
            
        await db.commit()
        await db.refresh(booking)
        return booking
        
    @staticmethod
    async def reject_booking(db: AsyncSession, booking: Booking, approver: Employee) -> Booking:
         if booking.status != BookingStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=400, detail="Booking is not pending approval.")
         
         old_status = booking.status
         booking.status = BookingStatus.REJECTED
         
         AuditService.log(
            db, "booking", booking.id, approver.id, "REJECT", 
            from_state=str(old_status.value), to_state=str(BookingStatus.REJECTED.value)
         )
         
         # Notify Booker
         stmt = select(Employee).where(Employee.id == booking.booker_id)
         result = await db.execute(stmt)
         booker = result.scalars().first()
         
         if booker:
            await NotificationService.send_email(
                booker.email,
                f"Booking Rejected: {booking.trip_name}",
                f"Your booking was rejected by {approver.full_name}."
            )

         await db.commit()
         await db.refresh(booking)
         return booking
