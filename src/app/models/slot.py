import uuid
from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models import Cafe


class Slot(Base):
    """Таблица слотов для бронирования."""

    cafe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('cafe.id', ondelete='CASCADE'),
        index=True,
        nullable=False,
    )
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    cafe: Mapped['Cafe'] = relationship(
        back_populates='slots',
        lazy='selectin',
    )

    __table_args__ = (
        UniqueConstraint(
            'cafe_id',
            'start_time',
            'end_time',
            name='uq_slots_cafe_window',
        ),
        UniqueConstraint('cafe_id', 'id', name='uq_slot_cafe_id_id'),
        CheckConstraint('start_time < end_time', name='ck_slot_interval'),
    )
