from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Any
import uuid

from app.api import deps
from app.db.session import get_db
from app.models.approval import ApprovalRequest, ApprovalStatus
from app.models.booking import Booking, BookingStatus
from app.models.employee import Employee
from app.schemas.approval import ApprovalRequestResponse, ApprovalAction
from app.services.booking_workflow import BookingStateMachine

router = APIRouter()

@router.get("/pending", response_model=List[ApprovalRequestResponse])
async def list_pending_approvals(
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List bookings waiting for MY approval.
    """
    stmt = select(ApprovalRequest).where(
        ApprovalRequest.approver_id == current_user.id,
        ApprovalRequest.status == ApprovalStatus.PENDING
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/{approval_id}/approve", response_model=ApprovalRequestResponse)
async def approve_request(
    approval_id: uuid.UUID,
    action: ApprovalAction,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # 1. Fetch Request
    stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    result = await db.execute(stmt)
    req = result.scalars().first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
        
    # 2. Verify Approver
    if req.approver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to approve this request")
        
    if req.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request is not pending")

    # 3. Update Request Status
    req.status = ApprovalStatus.APPROVED
    req.reason = action.reason
    db.add(req)
    
    # 4. Update Booking State via Workflow Service
    # Fetch booking
    stmt_b = select(Booking).where(Booking.id == req.booking_id)
    res_b = await db.execute(stmt_b)
    booking = res_b.scalars().first()
    
    if booking:
        await BookingStateMachine.approve_booking(db, booking, current_user)
    
    await db.commit()
    await db.refresh(req)
    return req

@router.post("/{approval_id}/reject", response_model=ApprovalRequestResponse)
async def reject_request(
    approval_id: uuid.UUID,
    action: ApprovalAction,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # 1. Fetch Request
    stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    result = await db.execute(stmt)
    req = result.scalars().first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
        
    if req.approver_id != current_user.id:
         raise HTTPException(status_code=403, detail="Not authorized to reject this request")

    if req.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request is not pending")

    # 2. Update Request Status
    req.status = ApprovalStatus.REJECTED
    req.reason = action.reason
    db.add(req)
    
    # 3. Update Booking State
    stmt_b = select(Booking).where(Booking.id == req.booking_id)
    res_b = await db.execute(stmt_b)
    booking = res_b.scalars().first()
    
    if booking:
        await BookingStateMachine.reject_booking(db, booking, current_user)

    await db.commit()
    await db.refresh(req)
    return req
