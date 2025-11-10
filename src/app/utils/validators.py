import re
from typing import Optional

from email_validator import EmailNotValidError
from email_validator import validate_email as ev_validate

from app.core.constants import (
    ALLOWED_SPECIAL_CHARS,
    PASSWORD_FORBIDS_OTHER_SYMBOLS,
    PASSWORD_MIN_LENGTH,
    PASSWORD_REQUIRES_DIGITS,
    PASSWORD_REQUIRES_LOWER_LETTERS,
    PASSWORD_REQUIRES_SPECIAL_CHARS,
    PASSWORD_REQUIRES_UPPER_LETTERS,
    PHONE_PATTERN,
)


def validate_email(value: Optional[str]) -> Optional[str]:
    """Возвращает читаемое сообщение при некорректном email."""
    if not (value and value.strip()):
        return None

    try:
        ev_validate(value, check_deliverability=False)
    except EmailNotValidError:
        raise ValueError(
            'Укажите адрес электронной почты, например: user@example.com',
        )
    return value


def validate_phone(value: Optional[str]) -> Optional[str]:
    """Возвращает читаемое сообщение при некорректном номере телефона."""
    if not (value and value.strip()):
        return None

    if not re.fullmatch(PHONE_PATTERN, value):
        raise ValueError(
            'Введите номер телефона в формате +XXXXXXXXX',
        )
    return value


def check_password_length(password: str, min_length: int) -> list[str]:
    """Проверяет пароль на соответствие длине."""
    if len(password) < min_length:
        return [f'длина не менее {min_length} символов']
    return []


def check_password_uppercase(password: str, required: bool) -> list[str]:
    """Проверяет пароль на наличие хотя бы одной заглавной буквы."""
    if required and not re.search(r'[A-Z]', password):
        return ['хотя бы одна заглавная буква']
    return []


def check_password_lowercase(password: str, required: bool) -> list[str]:
    """Проверяет пароль на наличие хотя бы одной строчной буквы."""
    if required and not re.search(r'[a-z]', password):
        return ['хотя бы одна строчная буква']
    return []


def check_password_digits(password: str, required: bool) -> list[str]:
    """Проверяет пароль на наличие хотя бы одной цифры."""
    if required and not re.search(r'\d', password):
        return ['хотя бы одна цифра']
    return []


def check_password_special_chars(
    password: str,
    required: bool,
    allowed_special: str,
) -> list[str]:
    """Проверяет пароль на наличие хотя бы одного спецсимвола из заданных."""
    if required and allowed_special:
        special_pattern = f'[{re.escape(allowed_special)}]'
        if not re.search(special_pattern, password):
            return [f'хотя бы один спецсимвол из: {allowed_special}']
    return []


def check_password_allowed_symbols(
    password: str,
    forbids_others: bool,
    allowed_special: str,
) -> list[str]:
    """Проверяет пароль на отсутствие неразрешённых символов."""
    if forbids_others:
        allowed_symbols = 'A-Za-z0-9' + (
            allowed_special if allowed_special else ''
        )
        pattern = f'^[{allowed_symbols}]+$'
        if not re.match(pattern, password):
            return [
                (
                    'запрещены иные символы кроме латиницы, цифр и символов: '
                    f'{allowed_special}'
                ),
            ]
    return []


def validate_password_strength(value: Optional[str]) -> Optional[str]:
    """Выполняет проверки пароля на соответствие требованиям."""
    errors = []
    errors.extend(check_password_length(value, PASSWORD_MIN_LENGTH))
    errors.extend(
        check_password_uppercase(value, PASSWORD_REQUIRES_UPPER_LETTERS),
    )
    errors.extend(
        check_password_lowercase(value, PASSWORD_REQUIRES_LOWER_LETTERS),
    )
    errors.extend(check_password_digits(value, PASSWORD_REQUIRES_DIGITS))
    errors.extend(
        check_password_special_chars(
            value,
            PASSWORD_REQUIRES_SPECIAL_CHARS,
            ALLOWED_SPECIAL_CHARS,
        ),
    )
    errors.extend(
        check_password_allowed_symbols(
            value,
            PASSWORD_FORBIDS_OTHER_SYMBOLS,
            ALLOWED_SPECIAL_CHARS,
        ),
    )
    if errors:
        raise ValueError('Пароль нарушает требования: ' + '; '.join(errors))
    return value
