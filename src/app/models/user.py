from typing import TYPE_CHECKING, List

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import CheckConstraint, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.utils.enums import UserRole

if TYPE_CHECKING:
    from app.models import Booking, Cafe


class User(SQLAlchemyBaseUserTableUUID, Base):
    """Расширенная таблица пользователей от FastAPI Users."""

    email: Mapped[str | None] = mapped_column(
        String(length=320),
        unique=True,
        index=True,
        nullable=True,
    )
    username: Mapped[str] = mapped_column(
        String(128),
        index=True,
        unique=True,
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(
        String(32),
        unique=True,
        nullable=True,
    )
    tg_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
    )
    role: Mapped[UserRole] = mapped_column(
        ENUM(UserRole, name='user_role', create_type=True),
        nullable=False,
        server_default=UserRole.USER.value,
    )

    cafe: Mapped['Cafe'] = relationship(
        secondary='cafemanager',
        back_populates='managers',
        single_parent=True,
        lazy='selectin',
    )
    booking: Mapped[List['Booking']] = relationship(
        back_populates='user',
        lazy='selectin',
    )

    __table_args__ = (
        CheckConstraint('phone IS NOT NULL OR email IS NOT NULL'),
    )
