from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Action, Cafe, Media
from app.repositories.base import CRUDBase
from app.schemas.action import ActionCreate, ActionUpdate


class ActionRepository(CRUDBase[Action, ActionCreate, ActionUpdate]):
    """Репозиторий для операций с акциями."""

    def __init__(self) -> None:
        """Инициализация репозитория акций."""
        super().__init__(Action)

    async def get_with_cafes(
        self,
        session: AsyncSession,
        action_id: UUID,
    ) -> Optional[Action]:
        """Получает акцию с информацией о связанных кафе."""
        return await self.get(
            session,
            id=action_id,
            options=[selectinload(Action.cafes)],
        )

    async def get_multi_with_cafes(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        show_all: bool = False,
        cafe_id: Optional[UUID] = None,
    ) -> List[Action]:
        """Получает список акций с информацией о кафе."""
        conditions = []
        if not show_all:
            conditions.append(Action.is_active.is_(True))
        if cafe_id:
            conditions.append(Action.cafes.any(id=cafe_id))
        return await self.get(
            session,
            *conditions,
            many=True,
            offset=skip,
            limit=limit,
            options=[selectinload(Action.cafes)],
        )

    async def create_with_cafes(
        self,
        session: AsyncSession,
        obj_in: ActionCreate,
    ) -> Action:
        """Создает акцию с привязкой к кафе."""
        cafes_ids = obj_in.cafes_id
        create_data = obj_in.model_dump(exclude={'cafes_id'})

        cafes = await self._fetch_cafes(session, cafes_ids)
        await self._ensure_photo_exists(session, create_data.get('photo_id'))

        db_obj = self.model(**create_data)
        db_obj.cafes.extend(cafes)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def update_with_cafes(
        self,
        session: AsyncSession,
        db_obj: Action,
        obj_in: ActionUpdate,
    ) -> Action:
        """Обновляет акцию и ее связи с кафе."""
        update_data = obj_in.model_dump(
            exclude_unset=True,
            exclude={'cafes_id'},
        )

        if 'photo_id' in update_data:
            await self._ensure_photo_exists(
                session,
                update_data.get('photo_id'),
            )

        for field, value in update_data.items():
            setattr(db_obj, field, value)
        if obj_in.cafes_id is not None:
            db_obj.cafes.clear()
            if obj_in.cafes_id:
                cafes = await self._fetch_cafes(session, obj_in.cafes_id)
                db_obj.cafes.extend(cafes)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def _fetch_cafes(
        self,
        session: AsyncSession,
        cafes_ids: list[UUID],
    ) -> list[Cafe]:
        """Возвращает список кафе, проверяя их существование и активность."""
        cafes_stmt = select(Cafe).where(
            Cafe.id.in_(cafes_ids),
            Cafe.is_active.is_(True),
        )
        cafes_result = await session.execute(cafes_stmt)
        cafes = cafes_result.scalars().all()
        if len(cafes) != len(set(cafes_ids)):
            raise ValueError('Некоторые кафе не найдены или отключены')
        return cafes

    async def _ensure_photo_exists(
        self,
        session: AsyncSession,
        photo_id: Optional[UUID],
    ) -> None:
        """Проверяет, что указанная фотография существует."""
        if photo_id is None:
            return
        photo = await session.get(Media, photo_id)
        if photo is None:
            raise ValueError('Указанное изображение не найдено')


action_repository = ActionRepository()
