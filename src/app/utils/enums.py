from enum import Enum


class UserRole(str, Enum):
    """Enum класс для ролей пользователей."""

    USER = 'USER'
    MANAGER = 'MANAGER'
    ADMIN = 'ADMIN'


class BookingStatus(str, Enum):
    """Enum класс для статусов бронирований."""

    CONFIRMED = 'CONFIRMED'
    CANCELED = 'CANCELED'
    DONE = 'DONE'
