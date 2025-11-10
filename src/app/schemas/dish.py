from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.types import StringConstraints

NameConstraint = StringConstraints(
    strip_whitespace=True,
    min_length=1,
    max_length=128,
)

DescriptionConstraint = StringConstraints(
    strip_whitespace=True,
    max_length=1000,
)


class DishBase(BaseModel):
    """Базовая схема для блюда."""

    name: Annotated[str, NameConstraint]
    description: Optional[Annotated[str, DescriptionConstraint]] = None
    price: Annotated[Decimal, Field(gt=0)]
    photo_id: Optional[UUID] = None
    is_active: Optional[bool] = True

    @field_validator('name', mode='before')
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Удаляет лишние пробелы и проверяет непустое название."""
        if not isinstance(value, str):
            raise ValueError('Название блюда должно быть строкой')
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Название блюда не может быть пустым')
        return cleaned

    @field_validator('description', mode='before')
    @classmethod
    def normalize_description(cls, value: Optional[str]) -> Optional[str]:
        """Удаляет лишние пробелы и приводит пустые описания к None."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Описание блюда должно быть строкой')
        cleaned = value.strip()
        return cleaned or None


class DishCreate(DishBase):
    """Схема для создания нового блюда."""

    cafes_id: list[UUID] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_cafes(self) -> 'DishCreate':
        """Проверяет уникальность списка кафе."""
        if not self.cafes_id:
            raise ValueError('Необходимо указать хотя бы одно кафе')
        if len(self.cafes_id) != len(set(self.cafes_id)):
            raise ValueError('Список кафе не должен содержать дубликаты')
        return self


class DishUpdate(BaseModel):
    """Схема для обновления существующего блюда."""

    name: Optional[Annotated[str, NameConstraint]] = None
    description: Optional[Annotated[str, DescriptionConstraint]] = None
    price: Optional[Annotated[Decimal, Field(gt=0)]] = None
    photo_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    cafes_id: Optional[list[UUID]] = None

    @field_validator('name', mode='before')
    @classmethod
    def normalize_name(cls, value: Optional[str]) -> Optional[str]:
        """Удаляет лишние пробелы из названия."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Название блюда должно быть строкой')
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Название блюда не может быть пустым')
        return cleaned

    @field_validator('description', mode='before')
    @classmethod
    def normalize_description(cls, value: Optional[str]) -> Optional[str]:
        """Удаляет лишние пробелы из описания."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Описание блюда должно быть строкой')
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode='after')
    def validate_cafes(self) -> 'DishUpdate':
        """Проверяет уникальность списка кафе при обновлении."""
        if self.cafes_id and len(self.cafes_id) != len(set(self.cafes_id)):
            raise ValueError('Список кафе не должен содержать дубликаты')
        return self


class DishShortInfo(BaseModel):
    """Сокращённая схема блюда для вложенных объектов."""

    id: UUID
    name: str
    price: Decimal
    photo_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class DishInfo(DishShortInfo):
    """Полная схема блюда со всеми связями."""

    description: Optional[str] = None
    cafes: list['CafeShortInfo'] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Импорт внизу, чтобы избежать циклических зависимостей
from app.schemas.cafe import CafeShortInfo  # noqa: E402

DishInfo.model_rebuild()
