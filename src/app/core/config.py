from pathlib import Path
from typing import Optional

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

BASE_DIR = Path(__file__).resolve().parents[3]
INFRA_DIR = BASE_DIR / 'infra'

LOG_DIR = BASE_DIR / 'logs'


class EmailSettings(BaseSettings):
    """Читает настройки из окружения с префиксом NOTIFY_."""

    MAIL_FROM: EmailStr
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    model_config = SettingsConfigDict(
        env_file=str(INFRA_DIR / '.env'),
        env_prefix='NOTIFY_',
        extra='allow',
    )


class Settings(BaseSettings):
    """Конфигурационный класс."""

    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_PORT: int
    POSTGRES_HOST: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: Optional[str] = None
    REDIS_CACHE_TTL: int

    LOG_LEVEL: str
    LOG_ROTATION: str
    LOG_RETENTION: str

    SECRET_KEY: str
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    RABBITMQ_DEFAULT_USER: str
    RABBITMQ_DEFAULT_PASS: str
    RABBITMQ_DEFAULT_VHOST: str
    RABBITMQ_DEFAULT_HOST: str
    RABBITMQ_DEFAULT_PORT: int

    ADMIN_USERNAME: str
    ADMIN_EMAIL: str
    ADMIN_PHONE: str
    ADMIN_TG_ID: str
    ADMIN_PASSWORD: str

    @property
    def db_url(self) -> URL:
        """Создает ссылку на подключение к Postgres."""
        return URL.create(
            drivername='postgresql+asyncpg',
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        )

    @property
    def rabbit_url(self) -> str:
        """Создает ссылку на подключение к RabbitMQ."""
        return (
            'amqp://'
            f'{self.RABBITMQ_DEFAULT_USER}:{self.RABBITMQ_DEFAULT_PASS}@'
            f'{self.RABBITMQ_DEFAULT_HOST}:{self.RABBITMQ_DEFAULT_PORT}/'
            f'{self.RABBITMQ_DEFAULT_VHOST}'
        )

    @property
    def redis_url(self) -> str:
        """URL для подключения к Redis."""
        if self.REDIS_PASSWORD:
            return (
                f'redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}'
                f':{self.REDIS_PORT}/{self.REDIS_DB}'
            )
        return f'redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}'

    model_config = SettingsConfigDict(
        env_file=str(INFRA_DIR / '.env'),
        extra='allow',
    )


settings = Settings()
email_settings = EmailSettings()
