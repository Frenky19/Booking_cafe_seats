from pydantic import BaseModel


class AuthToken(BaseModel):
    """Схема токена аутентификации."""

    access_token: str
    token_type: str = 'bearer'


class AuthData(BaseModel):
    """Схема для запроса логина."""

    login: str  # email или телефон
    password: str
