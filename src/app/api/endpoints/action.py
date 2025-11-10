from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.core.auth import role_checker
from app.core.db import DbSession
from app.core.dependencies import CacheServiceDep
from app.models.user import User
from app.repositories.action import action_repository
from app.schemas.action import ActionCreate, ActionInfo, ActionUpdate
from app.schemas.common import ErrorResponse
from app.services.cache_service import CacheService as CacheServiceType
from app.utils.enums import UserRole
from app.utils.http import build_error
from app.utils.logging_decorator import event_logger

router = APIRouter(prefix='/actions', tags=['Акции'])


def _get_actions_cache_key(show_all: bool, cafe_id: Optional[UUID]) -> str:
    """Генерация ключа кеша для списка акций."""
    base_key = f'actions:list:show_all={show_all}'
    if cafe_id:
        return f'{base_key}:cafe_id={cafe_id}'
    return base_key


def _get_action_cache_key(action_id: UUID) -> str:
    """Генерация ключа кеша для конкретной акции."""
    return f'actions:item:{action_id}'


@router.get(
    '/',
    response_model=list[ActionInfo],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_all_actions(
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
    cache: CacheServiceType = CacheServiceDep,
    show_all: bool = Query(False, description='Показывать все акции?'),
    cafe_id: UUID = Query(None, description='ID кафе'),
) -> list[ActionInfo]:
    """Получает список всех акций с кешированием."""
    try:
        cache_key = _get_actions_cache_key(show_all, cafe_id)
        cached_actions_data = await cache.get(cache_key)
        if cached_actions_data is not None:
            logger.debug(f'Кеш попадание для акций: {cache_key}')
            return [
                ActionInfo.model_validate(action_data)
                for action_data in cached_actions_data
            ]
        logger.debug(f'Кеш промах для акций: {cache_key}')
        db_actions = await action_repository.get_multi_with_cafes(
            session,
            show_all=show_all,
            cafe_id=cafe_id,
        )
        actions = [ActionInfo.model_validate(action) for action in db_actions]
        await cache.set(cache_key, [action.model_dump() for action in actions])
        return actions
    except Exception as e:
        logger.error(f'Ошибка при получении списка акций: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.post(
    '/',
    response_model=ActionInfo,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Создана', 'Action')
async def create_action(
    action_data: ActionCreate,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(role_checker([UserRole.MANAGER, UserRole.ADMIN])),
    ],
    cache: CacheServiceType = CacheServiceDep,
) -> ActionInfo:
    """Создает новую акцию и инвалидирует кеш."""
    try:
        db_action = await action_repository.create_with_cafes(
            session,
            action_data,
        )
        action = ActionInfo.model_validate(db_action)
        await cache.clear_actions_cache()
        logger.info('Кеш акций инвалидирован после создания новой акции')
        return action
    except ValueError as e:
        logger.error(f'Ошибка создания акции: {str(e)}')
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
        logger.error(f'Неожиданная ошибка при создании акции: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при создании акции',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.get(
    '/{action_id}',
    response_model=ActionInfo,
    responses={
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_action_by_id(
    action_id: UUID,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
    cache: CacheServiceType = CacheServiceDep,
) -> ActionInfo:
    """Получает информацию об акции по её идентификатору с кешированием."""
    try:
        cache_key = _get_action_cache_key(action_id)
        cached_action_data = await cache.get(cache_key)
        if cached_action_data is not None:
            logger.debug(f'Кеш попадание для акции: {cache_key}')
            return ActionInfo.model_validate(cached_action_data)
        logger.debug(f'Кеш промах для акции: {cache_key}')
        db_action = await action_repository.get_with_cafes(session, action_id)
        if not db_action:
            logger.warning(f'Акция {action_id} не найдена')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Акция не найдена',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        action = ActionInfo.model_validate(db_action)
        await cache.set(cache_key, action.model_dump())
        return action
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Ошибка при получении акции {action_id}: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.patch(
    '/{action_id}',
    response_model=ActionInfo,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Обновлена', 'Action')
async def update_action(
    action_id: UUID,
    update_data: ActionUpdate,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(role_checker([UserRole.MANAGER, UserRole.ADMIN])),
    ],
    cache: CacheServiceType = CacheServiceDep,
) -> ActionInfo:
    """Обновляет информацию об акции и инвалидирует кеш."""
    try:
        db_action = await action_repository.get_with_cafes(session, action_id)
        if not db_action:
            logger.warning(f'Акция {action_id} не найдена для обновления')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Акция не найдена',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        updated_db_action = await action_repository.update_with_cafes(
            session,
            db_action,
            update_data,
        )
        action = ActionInfo.model_validate(updated_db_action)
        await cache.delete(_get_action_cache_key(action_id))
        await cache.clear_actions_cache()
        logger.info(
            f'Кеш акций инвалидирован после обновления акции {action_id}',
        )
        return action
    except ValueError as e:
        logger.error(f'Ошибка обновления акции {action_id}: {str(e)}')
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
        logger.error(
            f'Неожиданная ошибка при обновлении акции {action_id}: {str(e)}',
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при обновлении акции',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )
