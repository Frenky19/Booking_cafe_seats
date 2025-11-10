import uuid
from datetime import datetime
from typing import Annotated, AsyncIterator

from fastapi import Depends
from sqlalchemy import UUID, Boolean, DateTime, func, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
)

from app.core.config import settings


class Base(DeclarativeBase):
    """Базовый класс для декларативного описания моделей."""

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        return cls.__name__.lower()

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text('true'),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


engine = create_async_engine(settings.db_url)

SessionFactory = async_sessionmaker(engine)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Функция для DI, которая создает асинхронную сессию SA."""
    async with SessionFactory() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_async_session)]
