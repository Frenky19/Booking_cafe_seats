import logging
import sys
from pathlib import Path

from loguru import logger

from app.core.config import (
    LOG_DIR,
    settings,
)
from app.core.constants import (
    FILE_LOG_FORMAT,
    INTERCEPTED_LOGGERS,
    LOG_COMPRESSION,
    LOG_DEPTH,
    LOG_ENCODING,
    LOG_FORMAT,
    get_logger_header,
)

_STD_INTERCEPT_CONFIGURED = False


class InterceptHandler(logging.Handler):
    """Перехват stdlib логов (uvicorn и sqlalchemy) в loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Передаёт запись стандартного логгера в Loguru."""
        try:
            lvl = logger.level(record.levelname).name
        except Exception:
            lvl = record.levelno
        logger.opt(
            depth=LOG_DEPTH,
            exception=False,
        ).log(lvl, record.getMessage())


def setup_stdlib_intercept() -> None:
    """Перенаправляет стандартные логи (uvicorn, sqlalchemy и др.) в Loguru."""
    global _STD_INTERCEPT_CONFIGURED
    if _STD_INTERCEPT_CONFIGURED:
        return
    root = logging.getLogger()
    root.handlers = [InterceptHandler()]
    root.setLevel(logging.NOTSET)

    for name in INTERCEPTED_LOGGERS:
        log = logging.getLogger(name)
        log.handlers = [InterceptHandler()]
        log.propagate = False
    _STD_INTERCEPT_CONFIGURED = True


def _ensure_defaults(record: dict) -> dict:
    """Добавляет значения по умолчанию в extra-поля лог-записи."""
    record['extra'].setdefault('username', 'SYSTEM')
    record['extra'].setdefault('user_id', '-')
    record['extra'].setdefault('request_id', '-')
    return record


def _write_log_header(path: Path) -> None:
    """Записывает заголовок с датой в начало лог-файла при его создании."""
    header = get_logger_header()
    try:
        with open(path, 'a', encoding=LOG_ENCODING) as f:
            f.write(header)
    except IOError as e:
        print(f'Не удалось записать заголовок в файл {path}: {e}')


def configure_logging() -> None:
    """Настраивает Loguru, создаёт sinks и подключает перехват логов stdlib."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / 'app.log'
    if not log_file.exists() or log_file.stat().st_size == 0:
        _write_log_header(log_file)

    logger.remove()
    logger.configure(patcher=_ensure_defaults)

    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format=LOG_FORMAT,
        colorize=True,
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )

    logger.add(
        log_file,
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression=LOG_COMPRESSION,
        format=FILE_LOG_FORMAT,
        encoding=LOG_ENCODING,
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )

    setup_stdlib_intercept()
