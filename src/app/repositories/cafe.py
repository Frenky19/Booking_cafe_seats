from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Cafe, Media, User
from app.repositories.base import CRUDBase
from app.schemas.cafe import CafeCreate, CafeUpdate
from app.utils.enums import UserRole


class CafeRepository(CRUDBase[Cafe, CafeCreate, CafeUpdate]):
    """Репозиторий для операций с кафе."""

    def __init__(self) -> None:
        """Инициализация репозитория кафе."""
        super().__init__(Cafe)

    async def get_with_managers(
        self,
        session: AsyncSession,
        cafe_id: UUID,
    ) -> Optional[Cafe]:
        """Получает кафе с информацией о менеджерах."""
        return await self.get(
            session,
            id=cafe_id,
            options=[selectinload(Cafe.managers)],
        )

    async def get_multi_with_managers(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        show_all: bool = False,
    ) -> List[Cafe]:
        """Получает список кафе с информацией о менеджерах."""
        conditions = []
        if not show_all:
            conditions.append(Cafe.is_active.is_(True))
        return await self.get(
            session,
            *conditions,
            many=True,
            offset=skip,
            limit=limit,
            options=[selectinload(Cafe.managers)],
        )

    async def create_with_managers(
        self,
        session: AsyncSession,
        obj_in: CafeCreate,
    ) -> Cafe:
        """Создает кафе с привязкой к менеджерам."""
        managers_ids = obj_in.managers_id
        create_data = obj_in.model_dump(exclude={'managers_id'})

        await self._ensure_unique_fields(
            session,
            name=create_data.get('name'),
            address=create_data.get('address'),
            phone=create_data.get('phone'),
        )

        await self._ensure_photo_exists(session, create_data.get('photo_id'))

        managers = await self._collect_managers(session, managers_ids)
        db_obj = self.model(**create_data)
        db_obj.managers.extend(managers)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def update_with_managers(
        self,
        session: AsyncSession,
        db_obj: Cafe,
        obj_in: CafeUpdate,
    ) -> Cafe:
        """Обновляет кафе и его связи с менеджерами."""
        update_data = obj_in.model_dump(
            exclude_unset=True,
            exclude={'managers_id'},
        )

        await self._ensure_unique_fields(
            session,
            name=update_data.get('name', db_obj.name),
            address=update_data.get('address', db_obj.address),
            phone=update_data.get('phone', db_obj.phone),
            exclude_id=db_obj.id,
        )

        if 'photo_id' in update_data:
            await self._ensure_photo_exists(
                session,
                update_data.get('photo_id'),
            )

        for field, value in update_data.items():
            setattr(db_obj, field, value)
        if obj_in.managers_id is not None:
            db_obj.managers.clear()
            managers = await self._collect_managers(
                session,
                obj_in.managers_id,
            )
            db_obj.managers.extend(managers)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def _ensure_unique_fields(
        self,
        session: AsyncSession,
        *,
        name: Optional[str] = None,
        address: Optional[str] = None,
        phone: Optional[str] = None,
        exclude_id: Optional[UUID] = None,
    ) -> None:
        """Проверяет уникальность ключевых полей кафе."""
        filters = []
        if exclude_id is not None:
            filters.append(Cafe.id != exclude_id)

        if name:
            stmt = select(Cafe.id).where(
                func.lower(Cafe.name) == name.lower(),
                *filters,
            )
            result = await session.execute(stmt)
            if result.scalars().first():
                raise ValueError('Кафе с таким названием уже существует')

        if address:
            stmt = select(Cafe.id).where(
                func.lower(Cafe.address) == address.lower(),
                *filters,
            )
            result = await session.execute(stmt)
            if result.scalars().first():
                raise ValueError('Кафе с таким адресом уже существует')

        if phone:
            stmt = select(Cafe.id).where(
                func.lower(Cafe.phone) == phone.lower(),
                *filters,
            )
            result = await session.execute(stmt)
            if result.scalars().first():
                raise ValueError('Кафе с таким телефоном уже существует')

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

    async def _collect_managers(
        self,
        session: AsyncSession,
        managers_ids: Optional[list[UUID]],
    ) -> list[User]:
        """Возвращает список менеджеров и валидирует их роли."""
        if not managers_ids:
            return []

        managers_stmt = select(User).where(User.id.in_(managers_ids))
        managers_result = await session.execute(managers_stmt)
        managers = managers_result.scalars().all()

        if len(managers) != len(managers_ids):
            raise ValueError('Некоторые менеджеры не найдены')

        invalid_roles = [
            manager.id
            for manager in managers
            if manager.role not in {UserRole.MANAGER, UserRole.ADMIN}
        ]
        if invalid_roles:
            raise ValueError(
                (
                    'Некоторые пользователи не имеют роли менеджера/админа: '
                    f'{
                        ", ".join(
                            str(manager_id) for manager_id in invalid_roles
                        )
                    }'
                ),
            )

        return managers


cafe_repository = CafeRepository()
