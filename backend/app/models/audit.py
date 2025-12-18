from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from typing import Optional
from app.db.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String, nullable=False) # e.g. "booking"
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    actor_id: Mapped[int] = mapped_column(Integer, nullable=False) # Employee ID
    action: Mapped[str] = mapped_column(String, nullable=False) # e.g. "SUBMIT", "APPROVE"
    
    from_state: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    to_state: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
