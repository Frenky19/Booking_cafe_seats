import json
from functools import wraps
from typing import Any, Callable

from loguru import logger


def _serialize(obj: Any, only_set: bool = True) -> dict | None:
    """Сериализует объект Pydantic в словарь для логирования."""
    if hasattr(obj, 'model_dump'):
        try:
            return obj.model_dump(
                mode='json',
                exclude_none=True,
                exclude_unset=only_set,
            )
        except Exception as e:
            logger.debug(
                f'Ошибка сериализации модели {e}',
            )
    return None


def event_logger(
    event_type: str,
    table_name: str,
    only_set: bool = True,
) -> Callable:
    """Декоратор для логирования выполнения эндпоинта.

    Логирует успешное выполнение асинхронной функции (эндпоинта)
    и возможные ошибки при выполнении операций с указанной таблицей.

    Args:
        event_type: Тип события ('Создание', 'Обновление', 'Удаление').
        table_name: Название таблицы, над которой выполняется операция.
        only_set: Флаг, указывающий сериализовать ли только заданные поля.
            По умолчанию True.

    Returns:
        Callable: Декоратор, оборачивающий асинхронную функцию и
            добавляющий логирование.

    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            parameters = next(
                (
                    data
                    for data in (
                        _serialize(v, only_set) for v in kwargs.values()
                    )
                    if data is not None
                ),
                None,
            )
            try:
                result = await func(*args, **kwargs)
                if parameters is not None:
                    formatted_params = json.dumps(
                        parameters,
                        ensure_ascii=False,
                        indent=4,
                    )
                    logger.info(
                        f'{event_type} запись в таблице "{table_name}", '
                        f'с параметрами:\n{formatted_params}',
                    )
                return result
            except Exception:
                logger.error(
                    f'Произошла ошибка при выполнении операции с '
                    f'таблицей "{table_name}"',
                )
                raise

        return wrapper

    return decorator
