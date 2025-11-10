import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import UUID, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models import (
        Action,
        Booking,
        Dish,
        Slot,
        Table,
        User,
    )


class Cafe(Base):
    """Таблица кафе."""

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    phone: Mapped[str] = mapped_column(
        String(15),
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    managers: Mapped[List['User']] = relationship(
        secondary='cafemanager',
        back_populates='cafe',
        lazy='selectin',
    )
    tables: Mapped[List['Table']] = relationship(
        back_populates='cafe',
        lazy='selectin',
    )
    slots: Mapped[List['Slot']] = relationship(
        back_populates='cafe',
        lazy='selectin',
    )
    dishes: Mapped[List['Dish']] = relationship(
        back_populates='cafes',
        secondary='dishcafe',
        lazy='selectin',
    )
    actions: Mapped[List['Action']] = relationship(
        back_populates='cafes',
        secondary='actioncafe',
        lazy='selectin',
    )
    booking: Mapped[List['Booking']] = relationship(
        back_populates='cafe',
        lazy='selectin',
    )
