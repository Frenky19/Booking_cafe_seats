from datetime import date
from uuid import UUID

from sqlalchemy import select

from app.core.db import DbSession
from app.models import Booking, ReservationUnit, Table
from app.utils.enums import BookingStatus


class AvailabilityService:
    """Сервис для проверки доступности столов и слотов."""

    @staticmethod
    async def check_tables_availability(
        session: DbSession,
        cafe_id: UUID,
        tables_ids: list[UUID],
        slots_ids: list[UUID],
        booking_date: date,
        exclude_booking_id: UUID | None = None,
    ) -> bool:
        """Проверяет доступность столов и временных слотов для бронирования.

        Args:
            session: Асинхронная сессия базы данных
            cafe_id: UUID кафе
            tables_ids: Список UUID столов для проверки
            slots_ids: Список UUID временных слотов для проверки
            booking_date: Дата бронирования
            exclude_booking_id: UUID бронирования для исключения
                                (при обновлении)

        Returns:
            bool: True если все столы и слоты доступны, False если есть
                  конфликты

        Raises:
            SQLAlchemyException: При ошибках работы с базой данных

        """
        for table_id in tables_ids:
            for slot_id in slots_ids:
                stmt = (
                    select(ReservationUnit)
                    .join(Booking)
                    .where(
                        ReservationUnit.table_id == table_id,
                        ReservationUnit.slot_id == slot_id,
                        ReservationUnit.booking_date == booking_date,
                        Booking.status != BookingStatus.CANCELED,
                        Booking.is_active.is_(True),
                    )
                )
                if exclude_booking_id:
                    stmt = stmt.where(Booking.id != exclude_booking_id)
                existing_booking_result = await session.execute(stmt)
                existing_booking = existing_booking_result.scalar_one_or_none()
                if existing_booking:
                    return False
        return True

    @staticmethod
    async def validate_tables_capacity(
        session: DbSession,
        tables_ids: list[UUID],
        guest_number: int,
    ) -> bool:
        """Проверяет достаточность количества мест выбранных столов.

        Args:
            session: Асинхронная сессия базы данных
            tables_ids: Список UUID столов для проверки
            guest_number: Количество гостей в бронировании

        Returns:
            bool: True если мест достаточно, False если недостаточно

        Raises:
            SQLAlchemyException: При ошибках работы с базой данных

        """
        stmt = select(Table).where(Table.id.in_(tables_ids))
        result = await session.execute(stmt)
        tables = result.scalars().all()
        if not tables:
            return False
        total_seats = sum(table.seat_number for table in tables)
        return total_seats >= guest_number

    @staticmethod
    async def validate_booking_date(booking_date: date) -> bool:
        """Проверяет корректность даты бронирования.

        Args:
            booking_date: Дата для проверки

        Returns:
            bool: True если дата корректна (не в прошлом), False если в прошлом

        """
        return booking_date >= date.today()
