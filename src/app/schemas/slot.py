from datetime import datetime, time
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic.types import StringConstraints

DescriptionConstraint = StringConstraints(
    strip_whitespace=True,
    min_length=1,
    max_length=300,
)


class SlotBase(BaseModel):
    """Базовая схема для временного слота с общими полями."""

    start_time: time
    end_time: time
    description: Annotated[str, DescriptionConstraint]

    @field_validator('description', mode='before')
    @classmethod
    def normalize_description(cls, value: str) -> str:
        """Удаляет лишние пробелы из описания."""
        if not isinstance(value, str):
            raise ValueError('Описание должно быть строкой')
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Описание не может быть пустым')
        return cleaned

    @model_validator(mode='after')
    def check_time_interval(self) -> 'SlotBase':
        """Проверяет, что время начала меньше времени окончания."""
        if self.start_time >= self.end_time:
            raise ValueError(
                'Время начала должно быть меньше времени окончания',
            )
        return self


class SlotCreate(SlotBase):
    """Схема для создания нового временного слота."""


class SlotUpdate(BaseModel):
    """Схема для обновления существующего временного слота."""

    cafe_id: Optional[UUID] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    description: Optional[Annotated[str, DescriptionConstraint]] = None
    is_active: Optional[bool] = None

    @field_validator('description', mode='before')
    @classmethod
    def normalize_description(cls, value: Optional[str]) -> Optional[str]:
        """Удаляет лишние пробелы и приводит пустые строки к None."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Описание должно быть строкой')
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode='after')
    def validate_time_range(self) -> 'SlotUpdate':
        """Проверяет корректность временного интервала при обновлении."""
        if self.start_time is not None and self.end_time is not None:
            if self.start_time >= self.end_time:
                raise ValueError(
                    'Время начала должно быть меньше времени окончания',
                )
        return self


class SlotShortInfo(BaseModel):
    """Сокращенная схема временного слота для вложенных объектов."""

    id: UUID
    start_time: time
    end_time: time
    description: str

    model_config = ConfigDict(from_attributes=True)


class SlotInfo(SlotShortInfo):
    """Полная схема временного слота со всей информацией и связями."""

    cafe: 'CafeShortInfo'
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


from app.schemas.cafe import CafeShortInfo  # noqa: E402

SlotInfo.model_rebuild()
