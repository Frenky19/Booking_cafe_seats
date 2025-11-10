import uuid
from datetime import date

from sqlalchemy import (
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ReservationUnit(Base):
    """Таблица атомов резервации столиков и слотов."""

    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('booking.id', ondelete='CASCADE'),
        index=True,
        nullable=False,
    )
    cafe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('cafe.id', ondelete='CASCADE'),
        index=True,
        nullable=False,
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('table.id', ondelete='RESTRICT'),
        nullable=False,
    )
    slot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('slot.id', ondelete='RESTRICT'),
        nullable=False,
    )
    booking_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            'table_id',
            'slot_id',
            'booking_date',
            name='uq_reservation_atom',
        ),
        ForeignKeyConstraint(
            ['cafe_id', 'table_id'],
            ['table.cafe_id', 'table.id'],
            name='fk_res_unit_table_cafe',
            ondelete='CASCADE',
        ),
        ForeignKeyConstraint(
            ['cafe_id', 'slot_id'],
            ['slot.cafe_id', 'slot.id'],
            name='fk_res_unit_slot_cafe',
            ondelete='CASCADE',
        ),
        Index('ix_res_units_cafe_date', 'cafe_id', 'booking_date'),
    )
