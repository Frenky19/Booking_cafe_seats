from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.core.auth import role_checker
from app.core.db import DbSession
from app.models.user import User
from app.repositories.slot import slot_repository
from app.schemas.common import ErrorResponse
from app.schemas.slot import SlotCreate, SlotInfo, SlotShortInfo, SlotUpdate
from app.utils.enums import UserRole
from app.utils.http import build_error
from app.utils.logging_decorator import event_logger

router = APIRouter(
    prefix='/cafe/{cafe_id}/time_slots',
    tags=['Временные слоты'],
)


@router.get(
    '/',
    response_model=list[SlotShortInfo],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_all_time_slots(
    cafe_id: UUID,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
    show_all: bool = Query(False, description='Показывать все слоты?'),
) -> list[SlotInfo]:
    """Получает список всех временных слотов в указанном кафе.

    Args:
        cafe_id: UUID идентификатор кафе
        session: Асинхронная сессия базы данных
        show_all: Флаг показа всех слотов (включая неактивные)
        current_user: Информация о текущем пользователе
    Returns:
        list[SlotInfo]: Список временных слотов кафе
    Raises:
        HTTPException: 404 если кафе не найдено
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        return await slot_repository.get_multi_by_cafe(
            session,
            cafe_id,
            show_all=show_all,
        )
    except Exception as e:
        logger.error(
            f'Ошибка при получении слотов для кафе {cafe_id}: {str(e)}',
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
    response_model=SlotInfo,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Создана', 'Slot')
async def create_time_slot(
    cafe_id: UUID,
    slot_data: SlotCreate,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(role_checker([UserRole.MANAGER, UserRole.ADMIN])),
    ],
) -> SlotInfo:
    """Создает новый временной слот в указанном кафе.

    Args:
        cafe_id: UUID идентификатор кафе
        slot_data: Данные для создания временного слота
        session: Асинхронная сессия базы данных
        current_user: Информация о текущем пользователе
    Returns:
        SlotInfo: Созданный объект временного слота
    Raises:
        HTTPException: 404 если кафе не найдено
        HTTPException: 400 если время начала >= времени окончания
        HTTPException: 400 если слот с таким интервалом уже существует
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        return await slot_repository.create_for_cafe(
            session,
            cafe_id,
            slot_data,
        )
    except ValueError as e:
        logger.error(f'Ошибка валидации при создании слота: {str(e)}')
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
        logger.error(f'Неожиданная ошибка при создании слота: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при создании слота',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.get(
    '/{slot_id}',
    response_model=SlotInfo,
    responses={
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_time_slot_by_id(
    cafe_id: UUID,
    slot_id: UUID,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
) -> SlotInfo:
    """Получает информацию о временном слоте по его ID в указанном кафе.

    Args:
        cafe_id: UUID идентификатор кафе
        slot_id: UUID идентификатор временного слота
        session: Асинхронная сессия базы данных
        current_user: Информация о текущем пользователе
    Returns:
        SlotInfo: Объект временного слота с полной информацией
    Raises:
        HTTPException: 404 если временной слот не найден
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        slot = await slot_repository.get_with_cafe(session, slot_id)
        if not slot or slot.cafe_id != cafe_id:
            logger.warning(f'Слот {slot_id} не найден в кафе {cafe_id}')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Временной слот не найден',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        return slot
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Ошибка при получении слота {slot_id}: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.patch(
    '/{slot_id}',
    response_model=SlotInfo,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Обновлена', 'Slot')
async def update_time_slot(
    cafe_id: UUID,
    slot_id: UUID,
    update_data: SlotUpdate,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(role_checker([UserRole.MANAGER, UserRole.ADMIN])),
    ],
) -> SlotInfo:
    """Обновляет информацию о временном слоте по его идентификатору.

    Args:
        cafe_id: UUID идентификатор кафе
        slot_id: UUID идентификатор временного слота
        update_data: Данные для обновления
        session: Асинхронная сессия базы данных
        current_user: Информация о текущем пользователе
    Returns:
        SlotInfo: Обновленный объект временного слота
    Raises:
        HTTPException: 404 если временной слот не найден
        HTTPException: 404 если новое кафе не найдено
        HTTPException: 400 если время начала >= времени окончания
        HTTPException: 400 если слот с таким интервалом уже существует
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        slot = await slot_repository.get_with_cafe(session, slot_id)
        if not slot or slot.cafe_id != cafe_id:
            logger.warning(f'Слот {slot_id} не найден для обновления')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Временной слот не найден',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        return await slot_repository.update_with_cafe_validation(
            session,
            slot,
            update_data,
            cafe_id,
        )
    except ValueError as e:
        logger.error(f'Ошибка валидации при обновлении слота: {str(e)}')
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
        logger.error(f'Неожиданная ошибка при обновлении слота: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при обновлении слота',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )
