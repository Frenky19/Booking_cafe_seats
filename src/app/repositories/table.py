from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Cafe, Table
from app.repositories.base import CRUDBase
from app.schemas.table import TableCreate, TableUpdate


class TableRepository(CRUDBase[Table, TableCreate, TableUpdate]):
    """Репозиторий для операций со столами."""

    def __init__(self) -> None:
        """Инициализация репозитория столов."""
        super().__init__(Table)

    async def get_with_cafe(
        self,
        session: AsyncSession,
        table_id: UUID,
    ) -> Optional[Table]:
        """Получает стол с информацией о кафе."""
        return await self.get(
            session,
            id=table_id,
            options=[selectinload(Table.cafe)],
        )

    async def get_multi_by_cafe(
        self,
        session: AsyncSession,
        cafe_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        show_all: bool = False,
    ) -> List[Table]:
        """Получает список столов для конкретного кафе."""
        conditions = [Table.cafe_id == cafe_id]
        if not show_all:
            conditions.append(Table.is_active.is_(True))
        return await self.get(
            session,
            *conditions,
            many=True,
            offset=skip,
            limit=limit,
            options=[selectinload(Table.cafe)],
        )

    async def create_for_cafe(
        self,
        session: AsyncSession,
        cafe_id: UUID,
        obj_in: TableCreate,
    ) -> Table:
        """Создает стол для конкретного кафе."""
        await self._ensure_cafe_exists(session, cafe_id)
        create_data = obj_in.model_dump(exclude={'cafe_id'})
        db_obj = self.model(**create_data, cafe_id=cafe_id)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def update_with_cafe_validation(
        self,
        session: AsyncSession,
        db_obj: Table,
        obj_in: TableUpdate,
        current_cafe_id: UUID,
    ) -> Table:
        """Обновляет стол с валидацией кафе и уникальности мест."""
        update_data = obj_in.model_dump(exclude_unset=True)

        if obj_in.cafe_id and obj_in.cafe_id != current_cafe_id:
            await self._ensure_cafe_exists(session, obj_in.cafe_id)

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


table_repository = TableRepository()
