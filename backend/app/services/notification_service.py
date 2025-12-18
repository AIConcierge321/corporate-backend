import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Mock Notification Service.
    In prod, connect to SES/SendGrid.
    """
    @staticmethod
    async def send_email(to_email: str, subject: str, body: str):
        # Simulate sending email
        # print is captured in logs which is good enough for now
        print(f"=================[EMAIL]=================")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        print(f"=========================================")
        logger.info(f"Email sent to {to_email}: {subject}")
