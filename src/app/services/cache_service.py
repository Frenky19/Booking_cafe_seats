import json
from datetime import datetime
from typing import Any, Optional

from loguru import logger
from redis.asyncio import Redis

from app.core.config import settings


class CacheService:
    """Сервис для работы с кешем Redis."""

    def __init__(self) -> None:
        """."""
        self.redis: Optional[Redis] = None
        self.ttl = settings.REDIS_CACHE_TTL

    async def connect(self) -> None:
        """Установка подключения к Redis."""
        try:
            self.redis = Redis.from_url(
                settings.redis_url,
                encoding='utf-8',
                decode_responses=True,
            )
            await self.redis.ping()
            logger.info('Успешное подключение к Redis')
        except Exception as e:
            logger.error(f'Ошибка подключения к Redis: {str(e)}')
            self.redis = None

    async def disconnect(self) -> None:
        """Закрытие подключения к Redis."""
        if self.redis:
            await self.redis.close()
            logger.info('Отключение от Redis')

    async def get(self, key: str) -> Optional[Any]:
        """Получение значения по ключу."""
        if not self.redis:
            return None
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f'Ошибка получения из кеша: {str(e)}')
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Сохранение значения в кеш."""
        if not self.redis:
            return False
        try:
            serialized_value = json.dumps(value, default=str)
            expire_time = ttl or self.ttl
            await self.redis.setex(key, expire_time, serialized_value)
            return True
        except Exception as e:
            logger.error(f'Ошибка сохранения в кеш: {str(e)}')
            return False

    async def delete(self, key: str) -> bool:
        """Удаление ключа из кеша."""
        if not self.redis:
            return False
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f'Ошибка удаления из кеша: {str(e)}')
            return False

    async def delete_pattern(self, pattern: str) -> bool:
        """Удаление ключей по шаблону."""
        if not self.redis:
            return False
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await self.redis.delete(*keys)
                logger.info(
                    f'Удалено ключей по шаблону {pattern}: {len(keys)}',
                )
            return True
        except Exception as e:
            logger.error(f'Ошибка удаления по шаблону: {str(e)}')
            return False

    async def clear_dishes_cache(self) -> None:
        """Очистка кеша блюд."""
        await self.delete_pattern('dishes:*')

    async def clear_actions_cache(self) -> None:
        """Очистка кеша акций."""
        await self.delete_pattern('actions:*')

    async def get_with_debug(
        self,
        key: str,
        debug_context: str = '',
    ) -> Optional[Any]:
        """Версия get с расширенным дебагом."""
        if not self.redis:
            logger.warning(f'Redis не подключен при запросе {key}')
            return None
        try:
            start_time: datetime = datetime.now()
            data: Optional[str] = await self.redis.get(key)
            request_time: float = (
                datetime.now() - start_time
            ).total_seconds() * 1000
            if data:
                logger.debug(
                    f'Кеш попадание: {key} | '
                    f'размер: {len(data)} байт | '
                    f'время: {request_time:.2f}мс | '
                    f'контекст: {debug_context}',
                )
                return json.loads(data)
            logger.debug(
                f'Кеш промах: {key} | '
                f'время: {request_time:.2f}мс | '
                f'контекст: {debug_context}',
            )
            return None
        except Exception as e:
            logger.error(f'Ошибка получения из кеша {key}: {str(e)}')
            return None

    async def set_with_debug(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        debug_context: str = '',
    ) -> bool:
        """Версия set с расширенным дебагом."""
        if not self.redis:
            logger.warning(f'Redis не подключен при сохранении {key}')
            return False
        try:
            serialized_value: str = json.dumps(value, default=str)
            expire_time: int = ttl or self.ttl
            start_time: datetime = datetime.now()
            result = await self.redis.setex(key, expire_time, serialized_value)
            request_time: float = (
                datetime.now() - start_time
            ).total_seconds() * 1000
            if result:
                logger.debug(
                    f'Успешно сохранено в кеш: {key} | '
                    f'размер: {len(serialized_value)} байт | '
                    f'TTL: {expire_time}сек | '
                    f'время: {request_time:.2f}мс | '
                    f'контекст: {debug_context}',
                )
            else:
                logger.warning(f'Не удалось сохранить в кеш: {key}')
            return bool(result)
        except Exception as e:
            logger.error(f'Ошибка сохранения в кеш {key}: {str(e)}')
            return False


cache_service = CacheService()
