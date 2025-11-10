from datetime import datetime

# Настройки требований к паролям
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRES_UPPER_LETTERS = True
PASSWORD_REQUIRES_LOWER_LETTERS = True
PASSWORD_REQUIRES_DIGITS = True
PASSWORD_REQUIRES_SPECIAL_CHARS = True
PASSWORD_FORBIDS_OTHER_SYMBOLS = True
ALLOWED_SPECIAL_CHARS = '!№;%:?*()_+-=:;<>,.~`'

# Настройки логгера
MS_IN_SECOND = 1000
LOG_DEPTH = 7
LOG_ENCODING = 'utf-8'
LOG_COMPRESSION = 'zip'
LOG_FORMAT = (
    '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | '
    '<level>{level: <8}</level> | '
    '{extra[username]}({extra[user_id]}) | '
    '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | '
    '<level>{message}</level>'
)
FILE_LOG_FORMAT = (
    '{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | '
    '{extra[username]}({extra[user_id]}) | '
    '{name}:{function}:{line} | {message}'
)
INTERCEPTED_LOGGERS = (
    'uvicorn',
    'uvicorn.error',
    'sqlalchemy',
    'celery',
)
NOISE_PATHS = {'/docs', '/openapi.json', '/health', '/livez', '/readyz'}
HTTP_LOG_TEMPLATE = (
    '{method} {path} -> {status} ({ms:.1f} ms)\n    ip={ip}\n    ua={ua}\n'
)

# Настройки медиа
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_IMAGE_FILE_SIZE = 5 * 1024 * 1024  # 5MB в байтах
JPEG_QUALITY = 85
MEDIA_DIR = 'media'  # Директория для хранения медиа файлов

# Разрешённый формат телефонного номера
PHONE_PATTERN = r'^\+[1-9][0-9]{7,14}$'


def get_logger_header() -> str:
    """Формирует заголовок для нового лог-файла."""
    return (
        '\n'
        '================= LOGGER - BOOKING_CAFE_SEATS =================\n'
        f'Date: {datetime.now():%Y-%m-%d %H:%M:%S}\n'
        '================================================================\n\n'
    )
