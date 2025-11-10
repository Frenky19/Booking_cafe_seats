from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Booking, Cafe, ReservationUnit, Slot, Table
from app.repositories.base import CRUDBase
from app.schemas.booking import BookingCreate, BookingUpdate
from app.services.availability_service import AvailabilityService
from app.utils.enums import BookingStatus


class BookingRepository(CRUDBase[Booking, BookingCreate, BookingUpdate]):
    """Репозиторий для операций с бронированиями."""

    def __init__(self) -> None:
        """Инициализация репозитория бронирований."""
        super().__init__(Booking)

    async def get_with_relations(
        self,
        session: AsyncSession,
        booking_id: UUID,
    ) -> Optional[Booking]:
        """Получает бронирование со всеми связями."""
        return await self.get(
            session,
            id=booking_id,
            options=[
                selectinload(Booking.user),
                selectinload(Booking.cafe),
                selectinload(Booking.tables),
                selectinload(Booking.slots),
            ],
        )

    async def get_multi_with_relations(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        show_all: bool = False,
        cafe_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> List[Booking]:
        """Получает список бронирований со всеми связями."""
        conditions = []
        if not show_all:
            conditions.append(Booking.is_active.is_(True))
        if cafe_id:
            conditions.append(Booking.cafe_id == cafe_id)
        if user_id:
            conditions.append(Booking.user_id == user_id)
        return await self.get(
            session,
            *conditions,
            many=True,
            offset=skip,
            limit=limit,
            options=[
                selectinload(Booking.user),
                selectinload(Booking.cafe),
                selectinload(Booking.tables),
                selectinload(Booking.slots),
            ],
        )

    async def create_with_validation(
        self,
        session: AsyncSession,
        obj_in: BookingCreate,
        user_id: UUID,
    ) -> Booking:
        """Создает бронирование с полной валидацией."""
        cafe_stmt = select(Cafe).where(Cafe.id == obj_in.cafe_id)
        cafe_result = await session.execute(cafe_stmt)
        cafe = cafe_result.scalar_one_or_none()
        if not cafe:
            raise ValueError('Кафе не найдено')
        if not await AvailabilityService.validate_booking_date(
            obj_in.booking_date,
        ):
            raise ValueError('Нельзя бронировать на прошедшие даты')
        await self._validate_relations(
            session,
            obj_in.cafe_id,
            obj_in.tables_id,
            obj_in.slots_id,
        )
        tables_stmt = select(Table).where(Table.id.in_(obj_in.tables_id))
        tables_result = await session.execute(tables_stmt)
        tables = tables_result.scalars().all()
        slots_stmt = select(Slot).where(Slot.id.in_(obj_in.slots_id))
        slots_result = await session.execute(slots_stmt)
        slots = slots_result.scalars().all()
        if not await AvailabilityService.validate_tables_capacity(
            session,
            obj_in.tables_id,
            obj_in.guest_number,
        ):
            total_seats = sum(table.seat_number for table in tables)
            raise ValueError(
                'Недостаточно мест: требуется '
                f'{obj_in.guest_number}, доступно {total_seats}',
            )
        if not await AvailabilityService.check_tables_availability(
            session,
            obj_in.cafe_id,
            obj_in.tables_id,
            obj_in.slots_id,
            obj_in.booking_date,
        ):
            raise ValueError('Выбранные столы и слоты уже заняты на эту дату')
        create_data = obj_in.model_dump(exclude={'tables_id', 'slots_id'})
        create_data['user_id'] = user_id
        db_obj = self.model(**create_data)
        session.add(db_obj)
        await session.flush()
        for table in tables:
            for slot in slots:
                reservation_unit = ReservationUnit(
                    booking_id=db_obj.id,
                    cafe_id=obj_in.cafe_id,
                    table_id=table.id,
                    slot_id=slot.id,
                    booking_date=obj_in.booking_date,
                )
                session.add(reservation_unit)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def update_with_validation(
        self,
        session: AsyncSession,
        db_obj: Booking,
        obj_in: BookingUpdate,
    ) -> Booking:
        """Обновляет бронирование с валидацией."""
        if db_obj.booking_date < date.today():
            raise ValueError('Нельзя изменять прошедшие бронирования')
        if db_obj.status == BookingStatus.DONE:
            raise ValueError('Нельзя изменять завершенные бронирования')
        update_data = obj_in.model_dump(
            exclude_unset=True,
            exclude={'tables_id', 'slots_id'},
        )
        if 'booking_date' in update_data:
            if not await AvailabilityService.validate_booking_date(
                update_data['booking_date'],
            ):
                raise ValueError('Нельзя бронировать на прошедшие даты')
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        if obj_in.tables_id is not None or obj_in.slots_id is not None:
            delete_units_stmt = delete(ReservationUnit).where(
                ReservationUnit.booking_id == db_obj.id,
            )
            await session.execute(delete_units_stmt)
            target_cafe_id = obj_in.cafe_id or db_obj.cafe_id
            target_booking_date = obj_in.booking_date or db_obj.booking_date
            target_tables_ids = obj_in.tables_id or [
                table.id for table in db_obj.tables
            ]
            target_slots_ids = obj_in.slots_id or [
                slot.id for slot in db_obj.slots
            ]
            await self._validate_relations(
                session,
                target_cafe_id,
                target_tables_ids,
                target_slots_ids,
            )
            for table_id in target_tables_ids:
                for slot_id in target_slots_ids:
                    reservation_unit = ReservationUnit(
                        booking_id=db_obj.id,
                        cafe_id=target_cafe_id,
                        table_id=table_id,
                        slot_id=slot_id,
                        booking_date=target_booking_date,
                    )
                    session.add(reservation_unit)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def _validate_relations(
        self,
        session: AsyncSession,
        cafe_id: UUID,
        tables_ids: List[UUID],
        slots_ids: List[UUID],
    ) -> None:
        """Проверяет наличие и активность таблиц и слотов для кафе."""
        if not tables_ids:
            raise ValueError('Необходимо указать хотя бы один стол')
        if not slots_ids:
            raise ValueError('Необходимо указать хотя бы один временной слот')

        tables_stmt = select(Table.id).where(
            Table.id.in_(tables_ids),
            Table.cafe_id == cafe_id,
            Table.is_active.is_(True),
        )
        tables_result = await session.execute(tables_stmt)
        db_tables = {row for row in tables_result.scalars().all()}
        if len(db_tables) != len(set(tables_ids)):
            raise ValueError(
                'Некоторые столы недоступны или относятся к другому кафе',
            )

        slots_stmt = select(Slot.id).where(
            Slot.id.in_(slots_ids),
            Slot.cafe_id == cafe_id,
            Slot.is_active.is_(True),
        )
        slots_result = await session.execute(slots_stmt)
        db_slots = {row for row in slots_result.scalars().all()}
        if len(db_slots) != len(set(slots_ids)):
            raise ValueError(
                'Некоторые временные слоты недоступны или '
                'относятся к другому кафе',
            )


booking_repository = BookingRepository()
