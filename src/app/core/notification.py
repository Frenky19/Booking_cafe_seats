from functools import lru_cache

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import email_settings


@lru_cache
def fastmail() -> FastMail:
    """Инициализация FastMail для настройки уведолмений."""
    conf = ConnectionConfig(
        MAIL_USERNAME=email_settings.MAIL_USERNAME,
        MAIL_PASSWORD=email_settings.MAIL_PASSWORD,
        MAIL_FROM=email_settings.MAIL_FROM,
        MAIL_PORT=email_settings.MAIL_PORT,
        MAIL_SERVER=email_settings.MAIL_SERVER,
        MAIL_STARTTLS=email_settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=email_settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=email_settings.USE_CREDENTIALS,
        VALIDATE_CERTS=email_settings.VALIDATE_CERTS,
    )
    return FastMail(conf)


async def send_notification(
    emails: list[str],
    text: str,
    subject: str,
    html: bool,
) -> None:
    """Функция на отправку уведомлений по SMTP."""
    message = MessageSchema(
        subject=subject,
        recipients=emails,
        body=text,
        subtype=MessageType.html if html else MessageType.plain,
    )
    await fastmail().send_message(message)
