from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditService:
    """
    Service to record audit logs for compliance and debugging.
    """

    @staticmethod
    def log(
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID,
        actor_id: int,
        action: str,
        from_state: str | None = None,
        to_state: str | None = None,
        details: dict | None = None,
    ):
        """
        Adds an audit log entry to the session.
        Does NOT commit; caller must commit.
        """
        log_entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            action=action,
            from_state=from_state,
            to_state=to_state,
            details=details,
        )
        db.add(log_entry)
