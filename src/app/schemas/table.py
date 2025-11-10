from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.types import StringConstraints

DescriptionConstraint = StringConstraints(
    strip_whitespace=True,
    max_length=300,
)
PositiveSeatNumber = Field(ge=1)


class TableBase(BaseModel):
    """Базовая схема для стола с общими полями."""

    description: Optional[Annotated[str, DescriptionConstraint]] = None
    seat_number: Annotated[int, PositiveSeatNumber]

    @field_validator('description', mode='before')
    @classmethod
    def normalize_description(cls, value: Optional[str]) -> Optional[str]:
        """Удаляет лишние пробелы и приводит пустые строки к None."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Описание стола должно быть строкой')
        cleaned = value.strip()
        return cleaned or None


class TableCreate(TableBase):
    """Схема для создания нового стола."""


class TableUpdate(BaseModel):
    """Схема для обновления существующего стола."""

    cafe_id: Optional[UUID] = None
    description: Optional[Annotated[str, DescriptionConstraint]] = None
    seat_number: Optional[Annotated[int, PositiveSeatNumber]] = None
    is_active: Optional[bool] = None

    @field_validator('description', mode='before')
    @classmethod
    def normalize_description(cls, value: Optional[str]) -> Optional[str]:
        """Удаляет лишние пробелы и приводит пустые строки к None."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Описание стола должно быть строкой')
        cleaned = value.strip()
        return cleaned or None


class TableShortInfo(BaseModel):
    """Сокращенная схема стола для вложенных объектов."""

    id: UUID
    description: Optional[str] = None
    seat_number: int

    model_config = ConfigDict(from_attributes=True)


class TableInfo(TableShortInfo):
    """Полная схема стола со всей информацией и связями."""

    cafe: 'CafeShortInfo'
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


from app.schemas.cafe import CafeShortInfo  # noqa: E402

TableInfo.model_rebuild()
