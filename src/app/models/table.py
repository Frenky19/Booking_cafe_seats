import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models import Cafe


class Table(Base):
    """Таблица столиков для бронирования."""

    cafe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('cafe.id', ondelete='CASCADE'),
        index=True,
        nullable=False,
    )
    seat_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    cafe: Mapped['Cafe'] = relationship(
        back_populates='tables',
        lazy='selectin',
    )

    __table_args__ = (
        UniqueConstraint('cafe_id', 'id', name='uq_table_cafe_id_id'),
        UniqueConstraint(
            'cafe_id',
            'seat_number',
            name='uq_table_number_per_cafe',
        ),
    )
