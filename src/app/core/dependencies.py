from fastapi import Depends

from app.services.cache_service import CacheService, cache_service


async def get_cache_service() -> CacheService:
    """Зависимость для получения сервиса кеширования."""
    return cache_service


CacheServiceDep = Depends(get_cache_service)
