from datetime import datetime
from typing import Optional

from celery_app.tasks import send_email_task

DEFAULT_SUBJECT = 'Уведомление о бронировании'


def send_notification_task(
    emails: list[str],
    text: str,
    subject: str = DEFAULT_SUBJECT,
    html: bool = False,
    countdown: Optional[int] = None,
    eta: Optional[datetime] = None,
) -> None:
    """Отправляет задачу в Celery на отправку уведомления.

    Args:
        emails (list[str]): список электронных адресов.
        text (str): текст уведомления.
        subject (str, optional): тема уведомления.
        html (bool, optional): флаг, указывающий, отправлять ли в HTML-формате.
        countdown (Optional[int]): через сколько секунд отправить уведомление.
        eta (Optional[datetime]): отправить уведомление к моменту времени.

    Note:
        Одновременно использовать eta и countdown нельзя.

    """
    if countdown and eta:
        raise ValueError('Нельзя одновременно использовать eta и countdown')

    send_email_task.apply_async(
        (emails, text, subject, html),
        countdown=countdown,
        eta=eta,
        queue='default',
    )
