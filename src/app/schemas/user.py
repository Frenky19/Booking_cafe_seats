from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    field_validator,
    model_validator,
)
from pydantic.types import StringConstraints

from app.core.constants import PHONE_PATTERN
from app.core.logging import logger
from app.utils.enums import UserRole
from app.utils.validators import (
    validate_email,
    validate_password_strength,
    validate_phone,
)

NameConstraint = StringConstraints(
    strip_whitespace=True,
    min_length=3,
    max_length=128,
)

TgConstraint = StringConstraints(strip_whitespace=True, max_length=64)


class UserBase(BaseModel):
    """Базовая схема для пользователя с основными полями."""

    username: Annotated[str, NameConstraint]
    email: Optional[EmailStr] = None
    phone: (
        Annotated[
            str,
            StringConstraints(pattern=PHONE_PATTERN),
        ]
        | None
    ) = None
    tg_id: Optional[Annotated[str, TgConstraint]] = None

    _validate_email = field_validator('email', mode='before')(validate_email)
    _validate_phone = field_validator('phone', mode='before')(validate_phone)


class UserCreate(UserBase):
    """Схема для создания нового пользователя."""

    password: str

    @model_validator(mode='after')
    def validate_phone_or_email(self) -> 'UserCreate':
        """Проверяет, что указан email или телефон."""
        if not self.phone and not self.email:
            raise ValueError('Необходимо указать email или телефон')
        return self

    @field_validator('password', mode='before')
    @classmethod
    def validate_password(cls, value: str) -> str:
        """Проверяет, что пароль соответствует требованиям."""
        return validate_password_strength(value)

    @field_validator('username', mode='before')
    @classmethod
    def normalize_username(cls, value: str) -> str:
        """Удаляет лишние пробелы и проверяет непустое имя пользователя."""
        if not isinstance(value, str):
            raise ValueError('Имя пользователя должно быть строкой')
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Имя пользователя не может быть пустым')
        return cleaned

    @field_validator('tg_id', mode='before')
    @classmethod
    def normalize_tg(cls, value: Optional[str]) -> Optional[str]:
        """Удаляет лишние пробелы в Telegram ID."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Telegram ID должен быть строкой')
        cleaned = value.strip()
        return cleaned or None


class UserUpdate(BaseModel):
    """Схема для обновления существующего пользователя."""

    username: Optional[Annotated[str, NameConstraint]] = None
    email: Optional[EmailStr] = None
    phone: (
        Annotated[
            str,
            StringConstraints(pattern=PHONE_PATTERN),
        ]
        | None
    ) = None
    tg_id: Optional[Annotated[str, TgConstraint]] = None
    role: Optional[int] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

    @field_validator('role', mode='before')
    @classmethod
    def validate_role(cls, value: int) -> int:
        """Валидация роли."""
        if value is not None:
            if value not in [0, 1, 2]:
                raise ValueError('Роль должна быть числом от 0 до 2')
        return value

    @field_validator('password', mode='before')
    @classmethod
    def validate_password(cls, value: Optional[str]) -> Optional[str]:
        """Проверяет, что пароль соответствует требованиям, если передан."""
        if value is None:
            return None
        return validate_password_strength(value)

    @field_validator('username', mode='before')
    @classmethod
    def normalize_username(cls, value: Optional[str]) -> Optional[str]:
        """Удаляет лишние пробелы из имени при обновлении."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Имя пользователя должно быть строкой')
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Имя пользователя не может быть пустым')
        return cleaned

    @field_validator('tg_id', mode='before')
    @classmethod
    def normalize_tg(cls, value: Optional[str]) -> Optional[str]:
        """Удаляет лишние пробелы из Telegram ID при обновлении."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Telegram ID должен быть строкой')
        cleaned = value.strip()
        return cleaned or None


class UserUpdateMe(BaseModel):
    """Схема для обновления самого себя."""

    username: Optional[Annotated[str, NameConstraint]] = None
    email: Optional[EmailStr] = None
    phone: (
        Annotated[
            str,
            StringConstraints(pattern=PHONE_PATTERN),
        ]
        | None
    ) = None
    tg_id: Optional[Annotated[str, TgConstraint]] = None
    password: Optional[str] = None

    @field_validator('password', mode='before')
    @classmethod
    def validate_password(cls, value: Optional[str]) -> Optional[str]:
        """Проверяет, что пароль соответствует требованиям, если передан."""
        if value is None:
            return None
        return validate_password_strength(value)

    @field_validator('username', mode='before')
    @classmethod
    def normalize_username(cls, value: Optional[str]) -> Optional[str]:
        """Удаляет лишние пробелы из имени пользователя."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Имя пользователя должно быть строкой')
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Имя пользователя не может быть пустым')
        return cleaned

    @field_validator('tg_id', mode='before')
    @classmethod
    def normalize_tg(cls, value: Optional[str]) -> Optional[str]:
        """Удаляет лишние пробелы в Telegram ID."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Telegram ID должен быть строкой')
        cleaned = value.strip()
        return cleaned or None


class UserShortInfo(UserBase):
    """Сокращенная схема пользователя для вложенных объектов."""

    id: UUID

    model_config = ConfigDict(from_attributes=True)


class UserInfo(UserShortInfo):
    """Полная схема пользователя со всей информацией."""

    role: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator('role', mode='before')
    @classmethod
    def convert_role_to_int(cls, v: UserRole) -> int:
        """Конвертирует роль в число для API."""
        if isinstance(v, int):
            return v
        try:
            if v == UserRole.USER:
                return 0
            if v == UserRole.MANAGER:
                return 1
            if v == UserRole.ADMIN:
                return 2
            return 0
        except Exception as e:
            logger.error(f'Ошибка конвертации роли: {e}')
            return 0
