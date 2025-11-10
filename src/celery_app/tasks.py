import asyncio

from fastapi_mail.errors import ConnectionErrors

from app.core.notification import send_notification
from celery_app.main import celery_app


@celery_app.task(name='send-notification')
def send_email_task(
    emails: list[str],
    text: str,
    subject: str,
    html: bool,
) -> int:
    """Таска на отправку уведомления о бронировании."""
    try:
        asyncio.run(
            send_notification(
                emails=emails,
                text=text,
                subject=subject,
                html=html,
            ),
        )
    except ConnectionErrors:
        raise
