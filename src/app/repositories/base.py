from typing import Any, Generic, Iterable, Optional, Sequence, Type, TypeVar

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Load

from app.core.db import Base
from app.models.user import User

ModelT = TypeVar('ModelT', bound=Base)
CreateSchemaT = TypeVar('CreateSchemaT', bound=BaseModel)
UpdateSchemaT = TypeVar('UpdateSchemaT', bound=BaseModel)


class CRUDBase(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    """Базовый класс для CRUD операций."""

    def __init__(self, model: Type[ModelT]) -> None:
        """Инициализация класса."""
        self.model = model

    async def get(
        self,
        session: AsyncSession,
        *predicates: Any,
        many: bool = False,
        order_by: Sequence[Any] = (),
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        options: Iterable[Load] = (),
        **filters: Any,
    ) -> list[ModelT] | ModelT:
        """Универсальная выборка по равенствам полям модели.

        get(..., field=value, ...).

        Параметры:
            session: AsyncSession.
            *predicates: произвольные SQLAlchemy-условия
            (например, Model.flag.is_(False)).
            many: True — вернуть список, False — вернуть первый или None.
            order_by, limit, offset: необязательные параметры выдачи.
            options: ORM-опции загрузки (selectinload и т.п.).
            **filters: равенства по полям модели (field=value).

        Исключения:
            ValueError — если передан фильтр по несуществующему полю модели.
        """
        self._validate_filters(filters)
        conditions = [getattr(self.model, k) == v for k, v in filters.items()]
        if predicates:
            conditions.extend(predicates)

        stmt = select(self.model).where(*conditions)
        if order_by:
            stmt = stmt.order_by(*order_by)
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        if options:
            stmt = stmt.options(*options)

        res = await session.execute(stmt)
        return list(res.scalars().all()) if many else res.scalars().first()

    async def get_multi(self, session: AsyncSession) -> list[ModelT]:
        """Получение всех записей из таблицы."""
        db_objs = await session.execute(select(self.model))

        return db_objs.scalars().all()

    async def create(
        self,
        obj_in: CreateSchemaT,
        session: AsyncSession,
        user: Optional[User] = None,
    ) -> ModelT:
        """Создание записи в БД."""
        obj_in_data = obj_in.dict(exclude_unset=True)
        if user is not None:
            obj_in_data['user_id'] = user.id

        db_obj = self.model(**obj_in_data)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def update_obj(
        self,
        db_obj: ModelT,
        obj_in: UpdateSchemaT,
        session: AsyncSession,
    ) -> ModelT:
        """Обновление записи в БД."""
        obj_data = jsonable_encoder(db_obj)
        update_data = obj_in.dict(exclude_unset=True)

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: ModelT, session: AsyncSession) -> ModelT:
        """Удаление записи из БД."""
        await session.delete(db_obj)
        await session.commit()
        return db_obj

    def _validate_filters(self, filters: dict[str, Any]) -> None:
        """Валидация фильтров, примененных к get()."""
        unknown = [k for k in filters if not hasattr(self.model, k)]
        if unknown:
            raise ValueError(
                'Некорректные поля фильтра для '
                f'{self.model.__name__}: {unknown}',
            )
