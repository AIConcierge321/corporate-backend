"""
SCIM Token Model

Stores organization-specific SCIM provisioning tokens for secure user sync.
"""

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, func, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
import secrets
from app.db.base import Base


class ScimToken(Base):
    """
    SCIM Bearer Token for IdP provisioning.
    
    Each organization can have multiple tokens (for rotation).
    Tokens are hashed before storage for security.
    """
    __tablename__ = "scim_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("organizations.id"), 
        nullable=False,
        index=True
    )
    
    # Token hash (we never store the raw token)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    
    # Friendly name for management (e.g., "Okta Production", "Azure AD Staging")
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Token metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="scim_tokens")
    
    @staticmethod
    def generate_token() -> tuple[str, str]:
        """
        Generate a new SCIM token and its hash.
        
        Returns: (raw_token, token_hash) - only return raw_token once!
        """
        import hashlib
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        return raw_token, token_hash
    
    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Hash a token for comparison."""
        import hashlib
        return hashlib.sha256(raw_token.encode()).hexdigest()
