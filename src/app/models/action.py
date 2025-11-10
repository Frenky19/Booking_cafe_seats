import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models import Cafe


class Action(Base):
    """Таблица об акциях в кафе."""

    description: Mapped[str] = mapped_column(Text, nullable=False)
    photo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    cafes: Mapped[List['Cafe']] = relationship(
        back_populates='actions',
        secondary='actioncafe',
        lazy='selectin',
    )
