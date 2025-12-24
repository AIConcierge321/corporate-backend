import enum
import uuid

from sqlalchemy import DateTime, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class IdPType(str, enum.Enum):
    OKTA = "okta"
    AZURE_AD = "azure_ad"
    GOOGLE_WORKSPACE = "google_workspace"
    OTHER = "other"


class ApprovalMode(str, enum.Enum):
    ALWAYS_ASK = "always_ask"
    ONLY_WHEN_NECESSARY = "only_when_necessary"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Identity Provider Config
    idp_type: Mapped[IdPType] = mapped_column(SQLEnum(IdPType), nullable=True)
    scim_tenant_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=True)

    # Policy Configuration
    approval_mode: Mapped[ApprovalMode] = mapped_column(
        SQLEnum(ApprovalMode), default=ApprovalMode.ALWAYS_ASK
    )
    policy_settings: Mapped[dict] = mapped_column(JSONB, default={})

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    employees: Mapped[list["Employee"]] = relationship(back_populates="organization")
    groups: Mapped[list["DirectoryGroup"]] = relationship(back_populates="organization")
    role_templates: Mapped[list["RoleTemplate"]] = relationship(back_populates="organization")
    scim_tokens: Mapped[list["ScimToken"]] = relationship(back_populates="organization")
