from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy import text

from app.core.db import DbSession
from app.core.dependencies import get_cache_service
from app.services.cache_service import CacheService
from app.services.notification import send_notification_task

router = APIRouter(prefix='/healthcheck', tags=['Healthcheck'])


@router.get('/db')
async def test(session: DbSession) -> Dict[str, str]:
    """Тестовая ручка на проверку состояния БД."""
    try:
        result = await session.execute(text('SELECT 1'))
        _ = result.scalar()
        logger.debug('Проверка БД: успешно')
        return {'status': 'ok'}
    except Exception as e:
        logger.error(f'Ошибка проверки БД: {str(e)}')
        return {'status': 'error', 'details': str(e)}


@router.get('/redis')
async def redis_health(
    cache: CacheService = Depends(get_cache_service),
) -> Dict[str, str]:
    """Проверка состояния Redis."""
    try:
        if cache.redis:
            await cache.redis.ping()
            logger.debug('Проверка Redis: успешно')
            return {'status': 'ok'}
        logger.error('Redis не подключен')
        return {'status': 'error', 'details': 'Redis не подключен'}
    except Exception as e:
        logger.error(f'Ошибка проверки Redis: {str(e)}')
        return {'status': 'error', 'details': str(e)}


@router.get('/cache')
async def test_cache(
    cache: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """Тестовый эндпоинт для проверки работы кеширования."""
    try:
        test_key: str = 'test:cache:demo'
        test_data: Dict[str, Any] = {
            'message': 'Тестовые данные для кеша',
            'timestamp': '2025-10-17T00:00:00',
            'numbers': [1, 2, 3, 4, 5],
        }
        save_result: bool = await cache.set_with_debug(
            test_key,
            test_data,
            ttl=60,
            debug_context='тестовый эндпоинт',
        )
        retrieved_data: Optional[Dict[str, Any]] = await cache.get_with_debug(
            test_key,
            debug_context='тестовый эндпоинт',
        )
        data_matches: bool = retrieved_data == test_data
        logger.debug(
            f'Тест кеша: сохранение={save_result}, совпадение={data_matches}',
        )
        return {
            'cache_available': cache.redis is not None,
            'save_successful': save_result,
            'data_retrieved': retrieved_data is not None,
            'data_matches': data_matches,
            'original_data': test_data,
            'retrieved_data': retrieved_data,
        }
    except Exception as e:
        logger.error(f'Ошибка тестирования кеша: {str(e)}')
        return {
            'cache_available': False,
            'save_successful': False,
            'data_retrieved': False,
            'data_matches': False,
            'error': str(e),
        }


@router.post('/email')
async def send_email_notification(email: str, text: str) -> dict[str, bool]:
    """Тестовая ручка для отправки уведомления."""
    try:
        send_notification_task([email], text)
        logger.info(f'Тестовое уведомление отправлено на {email}')
        return {'ok': True}
    except Exception as e:
        logger.error(f'Ошибка отправки тестового уведомления: {str(e)}')
        return {'ok': False, 'error': str(e)}
