import uuid
from datetime import date
from typing import TYPE_CHECKING, List

from sqlalchemy import Date, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.utils.enums import BookingStatus

if TYPE_CHECKING:
    from app.models import Cafe, Slot, Table, User


class Booking(Base):
    """Таблица бронирования столов и слотов в кафе."""

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('user.id', ondelete='CASCADE'),
        index=True,
        nullable=False,
    )
    cafe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('cafe.id', ondelete='CASCADE'),
        index=True,
        nullable=False,
    )
    booking_date: Mapped[date] = mapped_column(Date, nullable=False)
    guest_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        ENUM(BookingStatus, name='booking_status', create_type=True),
        nullable=False,
        server_default=BookingStatus.CONFIRMED.value,
    )
    note: Mapped[str] = mapped_column(Text, nullable=True)

    user: Mapped['User'] = relationship(
        back_populates='booking',
        uselist=False,
        lazy='selectin',
    )
    cafe: Mapped['Cafe'] = relationship(
        back_populates='booking',
        uselist=False,
        lazy='selectin',
    )
    tables: Mapped[List['Table']] = relationship(
        'Table',
        secondary='reservationunit',
        primaryjoin='Booking.id == foreign(ReservationUnit.booking_id)',
        secondaryjoin='Table.id == foreign(ReservationUnit.table_id)',
        viewonly=True,
        lazy='selectin',
    )
    slots: Mapped[List['Slot']] = relationship(
        'Slot',
        secondary='reservationunit',
        primaryjoin='Booking.id == foreign(ReservationUnit.booking_id)',
        secondaryjoin='Slot.id == foreign(ReservationUnit.slot_id)',
        viewonly=True,
        lazy='selectin',
    )
