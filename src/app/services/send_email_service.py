import hashlib
from datetime import datetime, timedelta
from uuid import UUID

from loguru import logger

from app.core.db import DbSession
from app.repositories.booking import booking_repository
from app.services.notification import send_notification_task


def generate_short_table_id(table_uuid: UUID) -> int:
    """Генерирует короткий числовой ID из UUID стола.

    Args:
        table_uuid: UUID стола (берется из table.id)

    Returns:
        Короткий числовой ID в диапазоне 1-9999

    """
    uuid_str = str(table_uuid)
    hash_object = hashlib.sha256(uuid_str.encode())
    hex_dig = hash_object.hexdigest()
    short_id = int(hex_dig[:4], 16)
    return short_id % 9999 + 1


class NotificationService:
    """Сервис для управления уведомлениями о бронированиях."""

    @staticmethod
    async def send_booking_created_notification(
        session: DbSession,
        booking_id: UUID,
        current_user_id: UUID,
    ) -> None:
        """Отправляет уведомление о создании бронирования."""
        try:
            booking = await booking_repository.get_with_relations(
                session,
                booking_id,
            )
            if not booking:
                logger.warning(
                    f'Бронирование {booking_id} не найдено для '
                    'уведомления о создании',
                )
                return
            user_email = booking.user.email
            manager_emails = [
                manager.email
                for manager in booking.cafe.managers
                if manager.email and manager.id != current_user_id
            ]
            emails = [user_email] + manager_emails
            emails = [email for email in emails if email]
            if not emails:
                logger.warning(
                    f'Нет email для отправки уведомления о создании '
                    f'бронирования {booking_id}',
                )
                return
            subject = 'Новое бронирование'
            time_slots = ', '.join(
                f'{slot.start_time.strftime("%H:%M")}-'
                f'{slot.end_time.strftime("%H:%M")}'
                for slot in booking.slots
            )
            tables_info = ', '.join(
                f'№{generate_short_table_id(table.id)} '
                f'({table.seat_number} мест)'
                for table in booking.tables
            )
            text = f"""
Новое бронирование создано:

Кафе: {booking.cafe.name}
Адрес: {booking.cafe.address}
Дата: {booking.booking_date}
Время: {time_slots}
Столы: {tables_info}
Количество гостей: {booking.guest_number}
Статус: {booking.status.value}
Заметка: {booking.note or 'Не указана'}

Бронирование создано пользователем: {booking.user.username}
"""
            send_notification_task(
                emails=emails,
                text=text,
                subject=subject,
            )
            logger.info(
                f'Уведомление о создании бронирования {booking_id} '
                'поставлено в очередь',
            )
        except Exception as e:
            logger.error(
                f'Ошибка отправки уведомления о создании бронирования '
                f'{booking_id}: {str(e)}',
            )
            raise

    @staticmethod
    async def send_booking_updated_notification(
        session: DbSession,
        booking_id: UUID,
        current_user_id: UUID,
    ) -> None:
        """Отправляет уведомление об изменении бронирования."""
        try:
            booking = await booking_repository.get_with_relations(
                session,
                booking_id,
            )
            if not booking:
                logger.warning(
                    f'Бронирование {booking_id} не найдено для '
                    'уведомления об изменении',
                )
                return
            user_email = booking.user.email
            manager_emails = [
                manager.email
                for manager in booking.cafe.managers
                if manager.email and manager.id != current_user_id
            ]
            emails = [user_email] + manager_emails
            emails = [email for email in emails if email]
            if not emails:
                logger.warning(
                    f'Нет email для отправки уведомления об изменении '
                    f'бронирования {booking_id}',
                )
                return
            subject = 'Изменение бронирования'
            time_slots = ', '.join(
                f'{slot.start_time.strftime("%H:%M")}-'
                f'{slot.end_time.strftime("%H:%M")}'
                for slot in booking.slots
            )
            tables_info = ', '.join(
                f'№{generate_short_table_id(table.id)} '
                f'({table.seat_number} мест)'
                for table in booking.tables
            )
            text = f"""
Бронирование изменено:

Кафе: {booking.cafe.name}
Адрес: {booking.cafe.address}
Дата: {booking.booking_date}
Время: {time_slots}
Столы: {tables_info}
Количество гостей: {booking.guest_number}
Статус: {booking.status.value}
Заметка: {booking.note or 'Не указана'}

Изменения внесены пользователем: {booking.user.username}
"""
            send_notification_task(
                emails=emails,
                text=text,
                subject=subject,
            )
            logger.info(
                f'Уведомление об изменении бронирования {booking_id} '
                'поставлено в очередь',
            )
        except Exception as e:
            logger.error(
                f'Ошибка отправки уведомления об изменении бронирования '
                f'{booking_id}: {str(e)}',
            )
            raise

    @staticmethod
    async def send_booking_reminder(
        session: DbSession,
        booking_id: UUID,
        reminder_minutes: int = 60,
    ) -> None:
        """Отправляет напоминание о бронировании."""
        try:
            booking = await booking_repository.get_with_relations(
                session,
                booking_id,
            )
            if not booking:
                logger.warning(
                    f'Бронирование {booking_id} не найдено для напоминания',
                )
                return
            if not booking.user.email:
                logger.warning(
                    f'У пользователя бронирования {booking_id} нет email '
                    'для напоминания',
                )
                return
            subject = (
                f'Напоминание о бронировании через {reminder_minutes} минут'
            )
            time_slots = ', '.join(
                f'{slot.start_time.strftime("%H:%M")}-'
                f'{slot.end_time.strftime("%H:%M")}'
                for slot in booking.slots
            )
            text = f"""
Напоминание о вашем бронировании:

Кафе: {booking.cafe.name}
Адрес: {booking.cafe.address}
Дата: {booking.booking_date}
Время: {time_slots}

"""
            booking_datetime = datetime.combine(
                booking.booking_date,
                booking.slots[0].start_time,
            )
            reminder_time = booking_datetime - timedelta(
                minutes=reminder_minutes,
            )
            if reminder_time < datetime.now():
                error_msg = (
                    f'Нельзя установить напоминание на прошедшее время '
                    f'для бронирования {booking_id}'
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            send_notification_task(
                emails=[booking.user.email],
                text=text,
                subject=subject,
                eta=reminder_time,
            )
            logger.info(
                f'Напоминание о бронировании {booking_id} запланировано '
                f'на {reminder_time}',
            )
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f'Ошибка отправки напоминания о бронировании {booking_id}: '
                f'{str(e)}',
            )
            raise
