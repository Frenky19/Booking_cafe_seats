from datetime import date, datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.utils.enums import BookingStatus


class BookingBase(BaseModel):
    """Базовая схема для бронирования с общими полями."""

    guest_number: Annotated[int, Field(ge=1, le=100)]
    note: Optional[str] = None
    status: BookingStatus
    booking_date: date

    @field_validator('note', mode='before')
    @classmethod
    def normalize_note(cls, value: Optional[str]) -> Optional[str]:
        """Очищает комментарий от лишних пробелов."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Комментарий должен быть строкой')
        cleaned = value.strip()
        return cleaned or None


class BookingCreate(BookingBase):
    """Схема для создания нового бронирования."""

    cafe_id: UUID
    tables_id: list[UUID]
    slots_id: list[UUID]

    @model_validator(mode='after')
    def validate_relations(self) -> 'BookingCreate':
        """Проверяет, что переданы корректные связи."""
        if not self.tables_id:
            raise ValueError('Необходимо выбрать хотя бы один стол')
        if not self.slots_id:
            raise ValueError('Необходимо выбрать хотя бы один временной слот')
        if len(self.tables_id) != len(set(self.tables_id)):
            raise ValueError('Список столов не должен содержать дубликаты')
        if len(self.slots_id) != len(set(self.slots_id)):
            raise ValueError('Список слотов не должен содержать дубликаты')
        return self


class BookingUpdate(BaseModel):
    """Схема для обновления существующего бронирования."""

    cafe_id: Optional[UUID] = None
    tables_id: Optional[list[UUID]] = None
    slots_id: Optional[list[UUID]] = None
    guest_number: Optional[Annotated[int, Field(ge=1, le=100)]] = None
    note: Optional[str] = None
    status: Optional[BookingStatus] = None
    booking_date: Optional[date] = None
    is_active: Optional[bool] = None

    @field_validator('note', mode='before')
    @classmethod
    def normalize_note(cls, value: Optional[str]) -> Optional[str]:
        """Очищает комментарий от лишних пробелов."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Комментарий должен быть строкой')
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode='after')
    def validate_relations(self) -> 'BookingUpdate':
        """Проверяет уникальность связей при обновлении."""
        if self.tables_id and len(self.tables_id) != len(set(self.tables_id)):
            raise ValueError('Список столов не должен содержать дубликаты')
        if self.slots_id and len(self.slots_id) != len(set(self.slots_id)):
            raise ValueError('Список слотов не должен содержать дубликаты')
        return self


class BookingInfo(BookingBase):
    """Полная схема бронирования со всей информацией и связями."""

    id: UUID
    user: 'UserShortInfo'
    cafe: 'CafeShortInfo'
    tables: list['TableShortInfo']
    slots: list['SlotShortInfo']
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookingShortInfo(BaseModel):
    """Сокращенная схема бронирования для списков."""

    id: UUID
    cafe: 'CafeShortInfo'
    booking_date: date
    status: BookingStatus
    guest_number: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


from app.schemas.cafe import CafeShortInfo  # noqa: E402
from app.schemas.slot import SlotShortInfo  # noqa: E402
from app.schemas.table import TableShortInfo  # noqa: E402
from app.schemas.user import UserShortInfo  # noqa: E402

BookingInfo.model_rebuild()
BookingShortInfo.model_rebuild()
