from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Cafe, Dish, Media
from app.repositories.base import CRUDBase
from app.schemas.dish import DishCreate, DishUpdate


class DishRepository(CRUDBase[Dish, DishCreate, DishUpdate]):
    """Репозиторий для операций с блюдами."""

    def __init__(self) -> None:
        """Инициализация репозитория блюд."""
        super().__init__(Dish)

    async def get_with_cafes(
        self,
        session: AsyncSession,
        dish_id: UUID,
    ) -> Optional[Dish]:
        """Получает блюдо с информацией о связанных кафе."""
        return await self.get(
            session,
            id=dish_id,
            options=[selectinload(Dish.cafes)],
        )

    async def get_multi_with_cafes(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        show_all: bool = False,
        cafe_id: Optional[UUID] = None,
    ) -> List[Dish]:
        """Получает список блюд с информацией о кафе."""
        conditions = []
        if not show_all:
            conditions.append(Dish.is_active.is_(True))
        if cafe_id:
            conditions.append(Dish.cafes.any(id=cafe_id))
        return await self.get(
            session,
            *conditions,
            many=True,
            offset=skip,
            limit=limit,
            options=[selectinload(Dish.cafes)],
        )

    async def create_with_cafes(
        self,
        session: AsyncSession,
        obj_in: DishCreate,
    ) -> Dish:
        """Создает блюдо с привязкой к кафе."""
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
        db_obj: Dish,
        obj_in: DishUpdate,
    ) -> Dish:
        """Обновляет блюдо и его связи с кафе."""
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
        """Возвращает список кафе, проверяя что они активны и существуют."""
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


dish_repository = DishRepository()
