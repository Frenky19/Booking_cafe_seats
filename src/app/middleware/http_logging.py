import base64
import json
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from loguru import logger

from app.core.constants import HTTP_LOG_TEMPLATE, MS_IN_SECOND, NOISE_PATHS


def _get_request_id(request: Request) -> str:
    """Возвращает X-Request-ID из заголовков или создаёт новый UUID."""
    return request.headers.get('X-Request-ID', str(uuid.uuid4()))


def _get_user_data(request: Request) -> tuple[str, str]:
    """Извлекает username и user_id или возвращает ('-', 'SYSTEM')."""
    auth = request.headers.get('authorization') or request.headers.get(
        'Authorization',
    )
    if auth and auth.lower().startswith('bearer '):
        try:
            payload_b64 = auth.split()[1].split('.')[1]
            payload_b64 += '=' * (-len(payload_b64) % 4)
            payload = json.loads(
                base64.urlsafe_b64decode(payload_b64).decode(),
            )
            uid = payload.get('user_id') or payload.get('sub') or '-'
            uname = payload.get('username') or payload.get('sub') or 'SYSTEM'
            return str(uid), str(uname)
        except Exception:
            pass
    return '-', 'SYSTEM'


def _get_client_ip(request: Request) -> str:
    """Возвращает IP-адрес клиента."""
    xff = request.headers.get('x-forwarded-for')
    if xff:
        return xff.split(',')[0].strip()
    return request.client.host if request.client else '-'


def _choose_level(status: int) -> str:
    """Возвращает уровень лога в зависимости от кода ответа."""
    if status >= 500:
        return 'ERROR'
    if 400 <= status < 500:
        return 'WARNING'
    return 'INFO'


async def logging_middleware(
    request: Request,
    call_next: Callable,
) -> Response:
    """Middleware для логирования HTTP-запросов.

    Добавляет контекст запроса (request_id, user_id, username) в лог,
    измеряет время обработки и логирует метод, путь, статус, IP-клиента
    и user-agent. Уровень лога выбирается по коду ответа:
    - INFO  — успешные ответы (2xx–3xx),
    - WARNING — клиентские ошибки (4xx),
    - ERROR — серверные ошибки (5xx).

    Не выводит пути (из NOISE_PATHS), кроме ошибок.
    """
    start = time.perf_counter()
    request_id = _get_request_id(request)
    path = request.url.path
    method = request.method
    client_ip = _get_client_ip(request)
    ua = request.headers.get('user-agent', '-')

    status = 500
    response: Response | None = None
    try:
        response = await call_next(request)
        status = response.status_code
    except Exception:
        logger.opt(exception=True).error(
            f'Необработанное исключение: {method} {path}',
        )
        raise
    finally:
        user_id, username = _get_user_data(request)
        ms = (time.perf_counter() - start) * MS_IN_SECOND
        level = _choose_level(status)
        should_log = (level == 'ERROR') or (path not in NOISE_PATHS)

        if should_log:
            with logger.contextualize(
                request_id=request_id,
                user_id=user_id,
                username=username,
            ):
                logger.log(
                    level,
                    HTTP_LOG_TEMPLATE,
                    method=method,
                    path=path,
                    status=status,
                    ms=ms,
                    ip=client_ip,
                    ua=ua,
                )

        if response is not None:
            response.headers.setdefault('X-Request-ID', request_id)

    return response
