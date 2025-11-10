from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.types import StringConstraints

from app.core.constants import PHONE_PATTERN
from app.utils.validators import validate_phone

NameConstraint = StringConstraints(
    strip_whitespace=True,
    min_length=1,
    max_length=128,
)

AddressConstraint = StringConstraints(
    strip_whitespace=True,
    min_length=1,
    max_length=300,
)

PhoneConstraint = StringConstraints(
    strip_whitespace=True,
    pattern=PHONE_PATTERN,
)


class CafeBase(BaseModel):
    """Базовая схема для кафе с общими полями."""

    name: Annotated[str, NameConstraint]
    address: Annotated[str, AddressConstraint]
    phone: Annotated[str, PhoneConstraint]
    description: Optional[str] = None
    photo_id: Optional[UUID] = None

    @field_validator('name', mode='after')
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Проверяет, что название кафе передано и не пустое."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Название кафе не может быть пустым')
        return value.strip()

    @field_validator('address', mode='after')
    @classmethod
    def validate_address(cls, value: str) -> str:
        """Проверяет, что адрес передан и не пустой."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Адрес кафе не может быть пустым')
        return value.strip()

    @field_validator('phone', mode='after')
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        """Проверяет корректность формата номера телефона."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Номер телефона обязателен для заполнения')
        return validate_phone(value.strip())

    @field_validator('description', mode='after')
    @classmethod
    def normalize_description(cls, value: Optional[str]) -> Optional[str]:
        """Очищает описание от лишних пробелов и пустых значений."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Описание должно быть строкой')
        cleaned = value.strip()
        return cleaned or None


class CafeCreate(CafeBase):
    """Схема для создания нового кафе."""

    managers_id: list[UUID] = Field(default_factory=list)

    @field_validator('managers_id', mode='after')
    @classmethod
    def validate_managers(cls, value: list[UUID]) -> list[UUID]:
        """Проверяет, что список менеджеров не содержит дубликатов."""
        if len(value) != len(set(value)):
            raise ValueError('Список менеджеров не должен содержать дубликаты')
        return value


class CafeUpdate(BaseModel):
    """Схема для обновления существующего кафе."""

    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    photo_id: Optional[UUID] = None
    managers_id: Optional[list[UUID]] = None
    is_active: Optional[bool] = None


class CafeShortInfo(BaseModel):
    """Сокращенная схема кафе для вложенных объектов."""

    id: UUID
    name: str
    address: str
    phone: str
    description: str
    photo_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class CafeInfo(CafeShortInfo):
    """Полная схема кафе со всей информацией и связями."""

    managers: list['UserShortInfo'] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Для избежания циклических импортов
from app.schemas.user import UserShortInfo  # noqa: E402

CafeInfo.model_rebuild()
