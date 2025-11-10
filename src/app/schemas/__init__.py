"""Модуль схем Pydantic для валидации и сериализации данных.

Содержит схемы для всех сущностей системы:
- Кафе (Cafe)
- Пользователи (User)
- Столы (Table)
- Временные слоты (Slot)
- Бронирования (Booking)
- Пользователи (User)
- Токен аутентификации (Auth)

Все схемы используют UUID для идентификаторов и поддерживают
валидацию данных.
"""

from .auth import AuthData, AuthToken
from .booking import (
    BookingCreate,
    BookingInfo,
    BookingShortInfo,
    BookingUpdate,
)
from .cafe import CafeCreate, CafeInfo, CafeShortInfo, CafeUpdate
from .common import ErrorResponse
from .media import CustomError, MediaData, MediaInfo
from .slot import SlotCreate, SlotInfo, SlotShortInfo, SlotUpdate
from .table import TableCreate, TableInfo, TableShortInfo, TableUpdate
from .user import UserCreate, UserInfo, UserShortInfo, UserUpdate, UserUpdateMe

__all__ = [
    'CafeCreate',
    'CafeInfo',
    'CafeShortInfo',
    'CafeUpdate',
    'UserCreate',
    'UserInfo',
    'UserShortInfo',
    'UserUpdate',
    'UserUpdateMe',
    'TableCreate',
    'TableInfo',
    'TableShortInfo',
    'TableUpdate',
    'SlotCreate',
    'SlotInfo',
    'SlotShortInfo',
    'SlotUpdate',
    'BookingCreate',
    'BookingInfo',
    'BookingShortInfo',
    'BookingUpdate',
    'MediaData',
    'MediaInfo',
    'CustomError',
    'ErrorResponse',
    'AuthToken',
    'AuthData',
]
