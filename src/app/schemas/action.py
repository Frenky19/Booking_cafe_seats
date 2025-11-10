from datetime import datetime
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


class ActionBase(BaseModel):
    """Базовая схема для акции."""

    description: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
    ]
    photo_id: Optional[UUID] = None
    is_active: Optional[bool] = True

    @field_validator('description', mode='before')
    @classmethod
    def normalize_description(cls, value: str) -> str:
        """Удаляет лишние пробелы и проверяет непустое описание."""
        if not isinstance(value, str):
            raise ValueError('Описание акции должно быть строкой')
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Описание акции не может быть пустым')
        return cleaned


class ActionCreate(ActionBase):
    """Схема для создания новой акции."""

    cafes_id: list[UUID] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_cafes(self) -> 'ActionCreate':
        """Проверяет уникальность списка кафе."""
        if not self.cafes_id:
            raise ValueError('Необходимо указать хотя бы одно кафе')
        if len(self.cafes_id) != len(set(self.cafes_id)):
            raise ValueError('Список кафе не должен содержать дубликаты')
        return self


class ActionUpdate(BaseModel):
    """Схема для обновления существующей акции."""

    description: Optional[
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True,
                min_length=1,
                max_length=500,
            ),
        ]
    ] = None
    photo_id: Optional[UUID] = None
    cafes_id: Optional[list[UUID]] = None
    is_active: Optional[bool] = None

    @field_validator('description', mode='before')
    @classmethod
    def normalize_description(cls, value: Optional[str]) -> Optional[str]:
        """Удаляет лишние пробелы и проверяет непустое значение."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Описание акции должно быть строкой')
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Описание акции не может быть пустым')
        return cleaned

    @model_validator(mode='after')
    def validate_cafes(self) -> 'ActionUpdate':
        """Проверяет уникальность списка кафе при обновлении."""
        if self.cafes_id and len(self.cafes_id) != len(set(self.cafes_id)):
            raise ValueError('Список кафе не должен содержать дубликаты')
        return self


class ActionShortInfo(BaseModel):
    """Сокращённая схема акции для вложенных объектов."""

    id: UUID
    description: str
    photo_id: Optional[UUID] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ActionInfo(ActionShortInfo):
    """Полная схема акции со всеми связями."""

    cafes: list['CafeShortInfo'] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Импорт внизу, чтобы избежать циклических зависимостей
from app.schemas.cafe import CafeShortInfo  # noqa: E402

ActionInfo.model_rebuild()
