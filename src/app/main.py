from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.endpoints import routers
from app.core.db import SessionFactory
from app.core.exception_handler import (
    http_exception_handler,
    validation_exception_handler,
)
from app.core.init_admin import upsert_admin_if_not_exist
from app.core.logging import configure_logging
from app.middleware.http_logging import logging_middleware
from app.services.cache_service import cache_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator:
    """Запускает логгер при запуске приложения."""
    configure_logging()
    await cache_service.connect()
    async with SessionFactory() as session:
        await upsert_admin_if_not_exist(session)
    yield
    await cache_service.disconnect()


app = FastAPI(
    title='Система бронирования мест в кафе',
    description='API для бронирования столов в кафе',
    version='0.1.0',
    lifespan=lifespan,
    root_path='/api',
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)

app.middleware('http')(logging_middleware)


for router in routers:
    app.include_router(router)
