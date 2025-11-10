from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.core.auth import role_checker
from app.core.db import DbSession
from app.models.user import User
from app.repositories.table import table_repository
from app.schemas.common import ErrorResponse
from app.schemas.table import (
    TableCreate,
    TableInfo,
    TableShortInfo,
    TableUpdate,
)
from app.utils.enums import UserRole
from app.utils.http import build_error
from app.utils.logging_decorator import event_logger

router = APIRouter(prefix='/cafe/{cafe_id}/tables', tags=['Столы'])


@router.get(
    '/',
    response_model=list[TableShortInfo],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_all_tables(
    cafe_id: UUID,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
    show_all: bool = Query(False, description='Показывать все столы?'),
) -> list[TableInfo]:
    """Получает список всех столов в указанном кафе.

    Args:
        cafe_id: UUID идентификатор кафе
        session: Асинхронная сессия базы данных
        show_all: Флаг показа всех столов (включая неактивные)
        current_user: Информация о текущем пользователе

    Returns:
        list[TableInfo]: Список столов кафе с информацией о кафе
    Raises:
        HTTPException: 404 если кафе не найдено
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        return await table_repository.get_multi_by_cafe(
            session,
            cafe_id,
            show_all=show_all,
        )
    except Exception as e:
        logger.error(
            f'Ошибка при получении столов для кафе {cafe_id}: {str(e)}',
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.post(
    '/',
    response_model=TableInfo,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Создана', 'Table')
async def create_table(
    cafe_id: UUID,
    table_data: TableCreate,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(role_checker([UserRole.MANAGER, UserRole.ADMIN])),
    ],
) -> TableInfo:
    """Создает новый стол в указанном кафе.

    Args:
        cafe_id: UUID идентификатор кафе
        table_data: Данные для создания стола
        session: Асинхронная сессия базы данных
        current_user: Информация о текущем пользователе
    Returns:
        TableInfo: Созданный объект стола с информацией о кафе
    Raises:
        HTTPException: 404 если кафе не найдено
        HTTPException: 400 если стол с таким количеством мест уже существует
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        return await table_repository.create_for_cafe(
            session,
            cafe_id,
            table_data,
        )
    except ValueError as e:
        logger.error(f'Ошибка валидации при создании стола: {str(e)}')
        status_code = (
            status.HTTP_404_NOT_FOUND
            if 'не найден' in str(e).lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail=build_error(str(e), status_code),
        )
    except Exception as e:
        logger.error(f'Неожиданная ошибка при создании стола: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при создании стола',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.get(
    '/{table_id}',
    response_model=TableInfo,
    responses={
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_table_by_id(
    cafe_id: UUID,
    table_id: UUID,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
) -> TableInfo:
    """Получает информацию о столе по его идентификатору в указанном кафе.

    Args:
        cafe_id: UUID идентификатор кафе
        table_id: UUID идентификатор стола
        session: Асинхронная сессия базы данных
        current_user: Информация о текущем пользователе
    Returns:
        TableInfo: Объект стола с полной информацией
    Raises:
        HTTPException: 404 если стол не найден
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        table = await table_repository.get_with_cafe(session, table_id)
        if not table or table.cafe_id != cafe_id:
            logger.warning(f'Стол {table_id} не найден в кафе {cafe_id}')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Стол не найден',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        return table
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Ошибка при получении стола {table_id}: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.patch(
    '/{table_id}',
    response_model=TableInfo,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Обновлена', 'Table')
async def update_table(
    cafe_id: UUID,
    table_id: UUID,
    update_data: TableUpdate,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(role_checker([UserRole.MANAGER, UserRole.ADMIN])),
    ],
) -> TableInfo:
    """Обновляет информацию о столе по его идентификатору.

    Args:
        cafe_id: UUID идентификатор кафе
        table_id: UUID идентификатор стола
        update_data: Данные для обновления
        session: Асинхронная сессия базы данных
        current_user: Информация о текущем пользователе
    Returns:
        TableInfo: Обновленный объект стола
    Raises:
        HTTPException: 404 если стол не найден
        HTTPException: 404 если новое кафе не найдено
        HTTPException: 400 если стол с таким количеством мест уже существует
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        table = await table_repository.get_with_cafe(session, table_id)
        if not table or table.cafe_id != cafe_id:
            logger.warning(f'Стол {table_id} не найден для обновления')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Стол не найден',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        return await table_repository.update_with_cafe_validation(
            session,
            table,
            update_data,
            cafe_id,
        )
    except ValueError as e:
        logger.error(f'Ошибка валидации при обновлении стола: {str(e)}')
        status_code = (
            status.HTTP_404_NOT_FOUND
            if 'не найден' in str(e).lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail=build_error(str(e), status_code),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Неожиданная ошибка при обновлении стола: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при обновлении стола',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )
