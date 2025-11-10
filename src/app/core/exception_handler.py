from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _format_error(code: int, detail: Any) -> dict[str, Any]:
    """Форматирует сообщение об ошибке в единый вид."""
    if isinstance(detail, dict):
        detail_code = detail.get('code', code)
        detail_str = detail.get('detail') or detail.get('message')
        if detail_str:
            return {'code': detail_code, 'detail': str(detail_str)}
        return {'code': detail_code, 'detail': str(detail)}
    if isinstance(detail, list):
        detail = '; '.join(str(item) for item in detail)
    return {'code': code, 'detail': str(detail) if detail else ''}


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Перехватывает ошибки валидации и возвращает понятные сообщения."""
    messages = [
        error['msg'].replace('Value error, ', '') for error in exc.errors()
    ]
    message = '; '.join(messages) if messages else 'Ошибка валидации данных'
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_format_error(status.HTTP_422_UNPROCESSABLE_CONTENT, message),
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Унифицирует формат ответа для HTTP исключений."""
    content = _format_error(exc.status_code, exc.detail)
    return JSONResponse(status_code=exc.status_code, content=content)
