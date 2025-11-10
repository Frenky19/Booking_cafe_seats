from datetime import time
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Cafe, Slot
from app.repositories.base import CRUDBase
from app.schemas.slot import SlotCreate, SlotUpdate


class SlotRepository(CRUDBase[Slot, SlotCreate, SlotUpdate]):
    """Репозиторий для операций со слотами."""

    def __init__(self) -> None:
        """Инициализация репозитория слотов."""
        super().__init__(Slot)

    async def get_with_cafe(
        self,
        session: AsyncSession,
        slot_id: UUID,
    ) -> Optional[Slot]:
        """Получает слот с информацией о кафе."""
        return await self.get(
            session,
            id=slot_id,
            options=[selectinload(Slot.cafe)],
        )

    async def get_multi_by_cafe(
        self,
        session: AsyncSession,
        cafe_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        show_all: bool = False,
    ) -> List[Slot]:
        """Получает список слотов для конкретного кафе."""
        conditions = [Slot.cafe_id == cafe_id]
        if not show_all:
            conditions.append(Slot.is_active.is_(True))

        return await self.get(
            session,
            *conditions,
            many=True,
            offset=skip,
            limit=limit,
            options=[selectinload(Slot.cafe)],
        )

    async def create_for_cafe(
        self,
        session: AsyncSession,
        cafe_id: UUID,
        obj_in: SlotCreate,
    ) -> Slot:
        """Создает слот для конкретного кафе."""
        await self._ensure_cafe_exists(session, cafe_id)
        await self._ensure_valid_interval(obj_in.start_time, obj_in.end_time)
        await self._ensure_no_overlap(
            session,
            cafe_id=cafe_id,
            start_time=obj_in.start_time,
            end_time=obj_in.end_time,
        )
        create_data = obj_in.model_dump(exclude={'cafe_id'})
        db_obj = self.model(**create_data, cafe_id=cafe_id)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def update_with_cafe_validation(
        self,
        session: AsyncSession,
        db_obj: Slot,
        obj_in: SlotUpdate,
        current_cafe_id: UUID,
    ) -> Slot:
        """Обновляет слот с валидацией кафе и временного интервала."""
        update_data = obj_in.model_dump(exclude_unset=True)
        target_cafe_id = obj_in.cafe_id or current_cafe_id

        if obj_in.cafe_id and obj_in.cafe_id != current_cafe_id:
            await self._ensure_cafe_exists(session, obj_in.cafe_id)

        start_time = obj_in.start_time or db_obj.start_time
        end_time = obj_in.end_time or db_obj.end_time
        await self._ensure_valid_interval(start_time, end_time)

        if (
            target_cafe_id != current_cafe_id
            or obj_in.start_time is not None
            or obj_in.end_time is not None
        ):
            await self._ensure_no_overlap(
                session,
                cafe_id=target_cafe_id,
                start_time=start_time,
                end_time=end_time,
                exclude_id=db_obj.id,
            )

        for field, value in update_data.items():
            setattr(db_obj, field, value)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def _ensure_cafe_exists(
        self,
        session: AsyncSession,
        cafe_id: UUID,
    ) -> Cafe:
        """Возвращает кафе или выбрасывает ошибку, если оно не найдено."""
        cafe = await session.get(Cafe, cafe_id)
        if cafe is None:
            raise ValueError('Кафе не найдено')
        return cafe

    async def _ensure_valid_interval(
        self,
        start_time: Optional[time],
        end_time: Optional[time],
    ) -> None:
        """Проверяет корректность временного интервала."""
        if start_time is None or end_time is None:
            raise ValueError('Не указано время начала или окончания слота')
        if start_time >= end_time:
            raise ValueError(
                'Время начала должно быть меньше времени окончания',
            )

    async def _ensure_no_overlap(
        self,
        session: AsyncSession,
        *,
        cafe_id: UUID,
        start_time: time,
        end_time: time,
        exclude_id: Optional[UUID] = None,
    ) -> None:
        """Проверяет, что интервал не пересекается с существующими слотами."""
        stmt = select(Slot).where(
            Slot.cafe_id == cafe_id,
            Slot.start_time < end_time,
            Slot.end_time > start_time,
        )
        if exclude_id:
            stmt = stmt.where(Slot.id != exclude_id)
        result = await session.execute(stmt)
        if result.scalars().first():
            raise ValueError(
                'Временной слот пересекается с существующим'
                'интервалом в этом кафе',
            )


slot_repository = SlotRepository()
