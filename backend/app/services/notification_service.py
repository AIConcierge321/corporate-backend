"""
Notification Service

MED-006: This is currently a MOCK service.
TODO: Integrate with SES/SendGrid/Mailgun for production.
"""

import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Log warning at module load if not in dev mode
if not settings.DEV_MODE:
    logger.warning(
        "⚠️  NotificationService is using MOCK implementation! "
        "Emails will NOT be sent. Configure a real email service for production."
    )


class NotificationService:
    """
    Mock email notification service.
    
    WARNING: This only prints to console. Replace with real email service
    (AWS SES, SendGrid, Mailgun) before production.
    """
    
    @staticmethod
    async def send_email(to: str, subject: str, body: str):
        """
        Send an email notification.
        
        Currently: prints to console.
        TODO: Integrate with real email provider.
        """
        logger.info(f"[MOCK EMAIL] To: {to}, Subject: {subject}")
        print(f"\n📧 Mock Email to: {to}\n   Subject: {subject}\n")

