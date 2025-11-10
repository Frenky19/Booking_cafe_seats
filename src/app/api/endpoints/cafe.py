from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.core.auth import role_checker
from app.core.db import DbSession
from app.models.user import User
from app.repositories.cafe import cafe_repository
from app.schemas.cafe import CafeCreate, CafeInfo, CafeUpdate
from app.schemas.common import ErrorResponse
from app.utils.enums import UserRole
from app.utils.http import build_error
from app.utils.logging_decorator import event_logger

router = APIRouter(prefix='/cafes', tags=['Кафе'])


@router.get(
    '/',
    response_model=list[CafeInfo],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_all_cafes(
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
    show_all: bool = Query(False, description='Показывать все кафе?'),
) -> list[CafeInfo]:
    """Получает список всех кафе с возможностью фильтрации по активности.

    Args:
        session: Асинхронная сессия базы данных
        show_all: Флаг показа всех кафе (включая неактивные)
        current_user: Информация о текущем пользователе
    Returns:
        list[CafeInfo]: Список объектов кафе с информацией о менеджерах
    Raises:
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        return await cafe_repository.get_multi_with_managers(
            session,
            show_all=show_all,
        )
    except Exception as e:
        logger.error(f'Ошибка при получении списка кафе: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.post(
    '/',
    response_model=CafeInfo,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Создана', 'Cafe')
async def create_cafe(
    cafe_data: CafeCreate,
    session: DbSession,
    current_user: Annotated[User, Depends(role_checker([UserRole.ADMIN]))],
) -> CafeInfo:
    """Создает новое кафе с указанными менеджерами.

    Args:
        cafe_data: Данные для создания кафе
        session: Асинхронная сессия базы данных
        current_user: Информация о текущем пользователе
    Returns:
        CafeInfo: Созданный объект кафе с информацией о менеджерах
    Raises:
        HTTPException: 400 если некоторые менеджеры не найдены
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        return await cafe_repository.create_with_managers(session, cafe_data)
    except ValueError as e:
        logger.error(f'Ошибка валидации при создании кафе: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_error(
                str(e),
                status.HTTP_400_BAD_REQUEST,
            ),
        )
    except Exception as e:
        logger.error(f'Неожиданная ошибка при создании кафе: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при создании кафе',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.get(
    '/{cafe_id}',
    response_model=CafeInfo,
    responses={
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_cafe_by_id(
    cafe_id: UUID,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
) -> CafeInfo:
    """Получает информацию о кафе по его идентификатору.

    Args:
        cafe_id: UUID идентификатор кафе
        session: Асинхронная сессия базы данных
        current_user: Информация о текущем пользователе
    Returns:
        CafeInfo: Объект кафе с полной информацией
    Raises:
        HTTPException: 404 если кафе не найдено
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        cafe = await cafe_repository.get_with_managers(session, cafe_id)
        if not cafe:
            logger.warning(f'Кафе {cafe_id} не найдено')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Кафе не найдено',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        return cafe
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Ошибка при получении кафе {cafe_id}: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.patch(
    '/{cafe_id}',
    response_model=CafeInfo,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Обновлена', 'Cafe')
async def update_cafe(
    cafe_id: UUID,
    update_data: CafeUpdate,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(role_checker([UserRole.MANAGER, UserRole.ADMIN])),
    ],
) -> CafeInfo:
    """Обновляет информацию о кафе по его идентификатору.

    Args:
        cafe_id: UUID идентификатор кафе
        update_data: Данные для обновления
        session: Асинхронная сессия базы данных
        current_user: Информация о текущем пользователе
    Returns:
        CafeInfo: Обновленный объект кафе
    Raises:
        HTTPException: 404 если кафе не найдено
        HTTPException: 400 если некоторые менеджеры не найдены
        SQLAlchemyException: При ошибках работы с базой данных

    """
    cafe = await cafe_repository.get_with_managers(session, cafe_id)
    if not cafe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=build_error(
                'Кафе не найдено',
                status.HTTP_404_NOT_FOUND,
            ),
        )
    try:
        return await cafe_repository.update_with_managers(
            session,
            cafe,
            update_data,
        )
    except ValueError as e:
        logger.error(f'Ошибка валидации при обновлении кафе: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_error(
                str(e),
                status.HTTP_400_BAD_REQUEST,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Неожиданная ошибка при обновлении кафе: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при обновлении кафе',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )
