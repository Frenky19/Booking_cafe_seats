from typing import Any


def build_error(detail: Any, code: int) -> dict[str, Any]:
    """Формирует унифицированный ответ об ошибке для API."""
    return {'code': code, 'detail': str(detail) if detail is not None else ''}
