import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CafeManager(Base):
    """Промежуточная таблица для связи между менеджерами и кафе."""

    id = None
    cafe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('cafe.id', ondelete='CASCADE'),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('user.id', ondelete='CASCADE'),
        primary_key=True,
    )


class DishCafe(Base):
    """Промежуточная таблица для связи между блюдами и кафе."""

    id = None
    dish_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('dish.id', ondelete='CASCADE'),
        primary_key=True,
    )
    cafe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('cafe.id', ondelete='CASCADE'),
        primary_key=True,
    )


class ActionCafe(Base):
    """Промежуточная таблица для связи между акциями и кафе."""

    id = None
    action_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('action.id', ondelete='CASCADE'),
        primary_key=True,
    )
    cafe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('cafe.id', ondelete='CASCADE'),
        primary_key=True,
    )
