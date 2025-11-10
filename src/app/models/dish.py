import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List

from sqlalchemy import Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models import Cafe


class Dish(Base):
    """Таблица блюд."""

    name: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    photo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    cafes: Mapped[List['Cafe']] = relationship(
        secondary='dishcafe',
        back_populates='dishes',
        lazy='selectin',
    )
