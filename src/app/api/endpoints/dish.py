from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.core.auth import role_checker
from app.core.db import DbSession
from app.core.dependencies import CacheServiceDep
from app.models.user import User
from app.repositories.dish import dish_repository
from app.schemas.common import ErrorResponse
from app.schemas.dish import DishCreate, DishInfo, DishUpdate
from app.services.cache_service import CacheService as CacheServiceType
from app.utils.enums import UserRole
from app.utils.http import build_error
from app.utils.logging_decorator import event_logger

router = APIRouter(prefix='/dishes', tags=['Блюда'])


def _get_dishes_cache_key(show_all: bool, cafe_id: Optional[UUID]) -> str:
    """Генерация ключа кеша для списка блюд."""
    base_key = f'dishes:list:show_all={show_all}'
    if cafe_id:
        return f'{base_key}:cafe_id={cafe_id}'
    return base_key


def _get_dish_cache_key(dish_id: UUID) -> str:
    """Генерация ключа кеша для конкретного блюда."""
    return f'dishes:item:{dish_id}'


@router.get(
    '/',
    response_model=list[DishInfo],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_all_dishes(
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
    cache: CacheServiceType = CacheServiceDep,
    show_all: bool = Query(False, description='Показывать все блюда?'),
    cafe_id: UUID = Query(None, description='ID кафе'),
) -> list[DishInfo]:
    """Получает список всех блюд с кешированием."""
    try:
        cache_key = _get_dishes_cache_key(show_all, cafe_id)
        cached_dishes = await cache.get(cache_key)
        if cached_dishes is not None:
            logger.debug(f'Кеш попадание для блюд: {cache_key}')
            return [
                DishInfo.model_validate(dish_data)
                for dish_data in cached_dishes
            ]
        logger.debug(f'Кеш промах для блюд: {cache_key}')
        db_dishes = await dish_repository.get_multi_with_cafes(
            session,
            show_all=show_all,
            cafe_id=cafe_id,
        )
        dishes = [DishInfo.model_validate(dish) for dish in db_dishes]
        await cache.set(cache_key, [dish.model_dump() for dish in dishes])
        return dishes
    except Exception as e:
        logger.error(f'Ошибка при получении списка блюд: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.post(
    '/',
    response_model=DishInfo,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Создана', 'Dish')
async def create_dish(
    dish_data: DishCreate,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(role_checker([UserRole.MANAGER, UserRole.ADMIN])),
    ],
    cache: CacheServiceType = CacheServiceDep,
) -> DishInfo:
    """Создает новое блюдо и инвалидирует кеш."""
    try:
        db_dish = await dish_repository.create_with_cafes(session, dish_data)
        dish = DishInfo.model_validate(db_dish)
        await cache.clear_dishes_cache()
        logger.info('Кеш блюд инвалидирован после создания нового блюда')
        return dish
    except ValueError as e:
        logger.error(f'Ошибка валидации при создании блюда: {str(e)}')
        error_code = (
            status.HTTP_404_NOT_FOUND
            if 'не найд' in str(e).lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=error_code,
            detail=build_error(str(e), error_code),
        )
    except Exception as e:
        logger.error(f'Неожиданная ошибка при создании блюда: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при создании блюда',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.get(
    '/{dish_id}',
    response_model=DishInfo,
    responses={
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_dish_by_id(
    dish_id: UUID,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
    cache: CacheServiceType = CacheServiceDep,
) -> DishInfo:
    """Получает информацию о блюде по его идентификатору с кешированием."""
    try:
        cache_key = _get_dish_cache_key(dish_id)
        cached_dish_data = await cache.get(cache_key)
        if cached_dish_data is not None:
            logger.debug(f'Кеш попадание для блюда: {cache_key}')
            return DishInfo.model_validate(cached_dish_data)
        logger.debug(f'Кеш промах для блюда: {cache_key}')
        db_dish = await dish_repository.get_with_cafes(session, dish_id)
        if not db_dish:
            logger.warning(f'Блюдо {dish_id} не найдено')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Блюдо не найдено',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        dish = DishInfo.model_validate(db_dish)
        await cache.set(cache_key, dish.model_dump())
        return dish
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Ошибка при получении блюда {dish_id}: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.patch(
    '/{dish_id}',
    response_model=DishInfo,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Обновлена', 'Dish')
async def update_dish(
    dish_id: UUID,
    update_data: DishUpdate,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(role_checker([UserRole.MANAGER, UserRole.ADMIN])),
    ],
    cache: CacheServiceType = CacheServiceDep,
) -> DishInfo:
    """Обновляет информацию о блюде и инвалидирует кеш."""
    try:
        db_dish = await dish_repository.get_with_cafes(session, dish_id)
        if not db_dish:
            logger.warning(f'Блюдо {dish_id} не найдено для обновления')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Блюдо не найдено',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        updated_db_dish = await dish_repository.update_with_cafes(
            session,
            db_dish,
            update_data,
        )
        dish = DishInfo.model_validate(updated_db_dish)
        await cache.delete(_get_dish_cache_key(dish_id))
        await cache.clear_dishes_cache()
        logger.info(f'Кеш блюд инвалидирован после обновления блюда {dish_id}')
        return dish
    except ValueError as e:
        logger.error(f'Ошибка валидации при обновлении блюда: {str(e)}')
        error_code = (
            status.HTTP_404_NOT_FOUND
            if 'не найд' in str(e).lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=error_code,
            detail=build_error(str(e), error_code),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Неожиданная ошибка при обновлении блюда: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при обновлении блюда',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )
