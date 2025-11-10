from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Базовая схема ответа с описанием ошибки."""

    code: int
    detail: str
