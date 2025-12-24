"""
Approval API Endpoints

Handles approval workflow with role-based permissions.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.access_control import AccessControl
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.approval import ApprovalRequest, ApprovalStatus
from app.models.booking import Booking
from app.models.employee import Employee
from app.schemas.approval import ApprovalAction, ApprovalRequestResponse
from app.services.booking_workflow import BookingStateMachine

router = APIRouter()


@router.get("/inbox", response_model=list[ApprovalRequestResponse])
@router.get("/pending", response_model=list[ApprovalRequestResponse])
@limiter.limit("30/minute")
async def list_pending_approvals(
    request: Request,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    List bookings waiting for MY approval (Inbox).

    Requires: approve_travel permission
    """
    ac = AccessControl(current_user)

    if not ac.can("approve_travel"):
        return []  # No approval permission = empty inbox

    stmt = select(ApprovalRequest).where(
        ApprovalRequest.approver_id == current_user.id,
        ApprovalRequest.status == ApprovalStatus.PENDING,
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{approval_id}/approve", response_model=ApprovalRequestResponse)
@limiter.limit("20/minute")
async def approve_request(
    request: Request,
    approval_id: uuid.UUID,
    action: ApprovalAction,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Approve a pending approval request.

    Requires: approve_travel permission
    """
    # Check permission
    ac = AccessControl(current_user)
    if not ac.can("approve_travel"):
        raise HTTPException(
            status_code=403, detail="You don't have permission to approve travel requests"
        )

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

    # 3. Fetch booking to check self-approval rule
    stmt_b = select(Booking).where(Booking.id == req.booking_id)
    res_b = await db.execute(stmt_b)
    booking = res_b.scalars().first()

    if booking:
        if booking.booker_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot approve your own booking.")

        await BookingStateMachine.approve_booking(db, booking, current_user)

    # 4. Update Request Status
    req.status = ApprovalStatus.APPROVED
    req.reason = action.reason
    db.add(req)

    await db.commit()
    await db.refresh(req)
    return req


@router.post("/{approval_id}/reject", response_model=ApprovalRequestResponse)
@limiter.limit("20/minute")
async def reject_request(
    request: Request,
    approval_id: uuid.UUID,
    action: ApprovalAction,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Reject a pending approval request.

    Requires: approve_travel permission
    """
    # Check permission
    ac = AccessControl(current_user)
    if not ac.can("approve_travel"):
        raise HTTPException(
            status_code=403, detail="You don't have permission to reject travel requests"
        )

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
