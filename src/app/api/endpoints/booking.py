from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import select

from app.core.auth import role_checker
from app.core.db import DbSession
from app.models import User
from app.repositories.booking import booking_repository
from app.schemas.booking import (
    BookingCreate,
    BookingInfo,
    BookingShortInfo,
    BookingUpdate,
)
from app.schemas.common import ErrorResponse
from app.services.send_email_service import NotificationService
from app.utils.enums import UserRole
from app.utils.http import build_error
from app.utils.logging_decorator import event_logger

router = APIRouter(prefix='/booking', tags=['Бронирования'])


@router.get(
    '/',
    response_model=list[BookingShortInfo],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_all_booking(
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
    show_all: bool = Query(False, description='Показывать все бронирования?'),
    cafe_id: UUID = Query(None, description='ID кафе'),
    user_id: UUID = Query(None, description='ID пользователя'),
) -> list[BookingInfo]:
    """Получает список бронирований с возможностью фильтрации.

    Args:
        session: Асинхронная сессия базы данных
        show_all: Флаг показа всех бронирований (включая неактивные)
        cafe_id: Фильтр по идентификатору кафе
        user_id: Фильтр по идентификатору пользователя
        current_user: Информация о текущем пользователе
    Returns:
        list[BookingInfo]: Список бронирований с полной информацией
    Raises:
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        return await booking_repository.get_multi_with_relations(
            session,
            show_all=show_all,
            cafe_id=cafe_id,
            user_id=user_id,
        )
    except Exception as e:
        logger.error(f'Ошибка при получении списка бронирований: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.post(
    '/',
    response_model=BookingInfo,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Создана', 'Booking')
async def create_booking(
    booking_data: BookingCreate,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
) -> BookingInfo:
    """Создает новое бронирование с полной валидацией бизнес-правил.

    Args:
        booking_data: Данные для создания бронирования
        session: Асинхронная сессия базы данных
        current_user: Информация о текущем пользователе
    Returns:
        BookingInfo: Созданный объект бронирования с полной информацией
    Raises:
        HTTPException: 404 если кафе, столы или слоты не найдены
        HTTPException: 400 если недостаточно мест для гостей
        HTTPException: 400 если дата бронирования в прошлом
        HTTPException: 400 если выбранные столы и слоты уже заняты
        HTTPException: 400 если пользователь не найден
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        if not current_user:
            logger.warning('Пользователь не найден при создании бронирования')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=build_error(
                    'Пользователь не найден',
                    status.HTTP_400_BAD_REQUEST,
                ),
            )
        booking = await booking_repository.create_with_validation(
            session,
            booking_data,
            current_user.id,
        )
        try:
            await NotificationService.send_booking_created_notification(
                session,
                booking.id,
                current_user.id,
            )
            logger.info(
                f'Уведомление о создании бронирования {booking.id} отправлено',
            )
        except Exception as e:
            logger.error(f'Ошибка отправки уведомления: {str(e)}')
        return booking
    except ValueError as e:
        logger.error(f'Ошибка валидации при создании бронирования: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_error(str(e), status.HTTP_400_BAD_REQUEST),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Неожиданная ошибка при создании бронирования: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при создании бронирования',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.get(
    '/{booking_id}',
    response_model=BookingInfo,
    responses={
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_booking_by_id(
    booking_id: UUID,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
) -> BookingInfo:
    """Получает информацию о бронировании по его идентификатору.

    Args:
        booking_id: UUID идентификатор бронирования
        session: Асинхронная сессия базы данных
        current_user: Информация о текущем пользователе
    Returns:
        BookingInfo: Объект бронирования с полной информацией
    Raises:
        HTTPException: 404 если бронирование не найдено
        SQLAlchemyException: При ошибках работы с базой данных

    """
    try:
        booking = await booking_repository.get_with_relations(
            session,
            booking_id,
        )
        if not booking:
            logger.warning(f'Бронирование {booking_id} не найдено')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Бронирование не найдено',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        return booking
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f'Ошибка при получении бронирования {booking_id}: {str(e)}',
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.patch(
    '/{booking_id}',
    response_model=BookingInfo,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Обновлена', 'Booking')
async def update_booking(
    booking_id: UUID,
    update_data: BookingUpdate,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(
            role_checker([UserRole.MANAGER, UserRole.ADMIN, UserRole.USER]),
        ),
    ],
) -> BookingInfo:
    """Обновляет информацию о бронировании с валидацией данных.

    Args:
        booking_id: UUID идентификатор бронирования
        update_data: Данные для обновления
        session: Асинхронная сессия базы данных
        current_user: Информация о текущем пользователе
    Returns:
        BookingInfo: Обновленный объект бронирования
    Raises:
        HTTPException: 404 если бронирование не найдено
        HTTPException: 400 если нельзя изменять прошедшие бронирования
        HTTPException: 400 если нельзя изменять завершенные бронирования
        SQLAlchemyException: При ошибках работы с базой данных

    """
    booking = await booking_repository.get_with_relations(session, booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=build_error(
                'Бронирование не найдено',
                status.HTTP_404_NOT_FOUND,
            ),
        )
    try:
        user_stmt = select(User).limit(1)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            logger.warning(
                'Пользователь не найден при обновлении бронирования',
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=build_error(
                    'Пользователь не найден',
                    status.HTTP_400_BAD_REQUEST,
                ),
            )
        booking = await booking_repository.get_with_relations(
            session,
            booking_id,
        )
        if not booking:
            logger.warning(
                f'Бронирование {booking_id} не найдено для обновления',
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Бронирование не найдено',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        updated_booking = await booking_repository.update_with_validation(
            session,
            booking,
            update_data,
        )
        try:
            await NotificationService.send_booking_updated_notification(
                session,
                booking_id,
                user.id,
            )
            logger.info(
                f'Уведомление об изменении бронирования {booking_id} '
                'отправлено',
            )
        except Exception as e:
            logger.error(f'Ошибка отправки уведомления: {str(e)}')
        return updated_booking
    except ValueError as e:
        logger.error(f'Ошибка валидации при обновлении бронирования: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_error(str(e), status.HTTP_400_BAD_REQUEST),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f'Неожиданная ошибка при обновлении бронирования: {str(e)}',
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при обновлении бронирования',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.post(
    '/{booking_id}/reminder',
    responses={
        status.HTTP_200_OK: {'model': dict},
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def schedule_booking_reminder(
    booking_id: UUID,
    session: DbSession,
    reminder_minutes: int = Query(
        60,
        description='За сколько минут напоминать',
    ),
) -> dict:
    """Планирует напоминание о бронировании."""
    try:
        booking = await booking_repository.get_with_relations(
            session,
            booking_id,
        )
        if not booking:
            logger.warning(
                f'Бронирование {booking_id} не найдено для напоминания',
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Бронирование не найдено',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        if not booking.user.email:
            logger.warning(
                f'У пользователя {booking.user.id} нет email для напоминания',
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=build_error(
                    'У пользователя нет email для отправки напоминания',
                    status.HTTP_400_BAD_REQUEST,
                ),
            )
        await NotificationService.send_booking_reminder(
            session,
            booking_id,
            reminder_minutes,
        )
        return {
            'status': 'success',
            'message': (
                f'Напоминание запланировано за {reminder_minutes} '
                'минут до бронирования'
            ),
        }
    except ValueError as e:
        logger.error(
            f'Ошибка валидации при планировании напоминания: {str(e)}',
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_error(str(e), status.HTTP_400_BAD_REQUEST),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Ошибка планирования напоминания: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                f'Ошибка планирования напоминания: {str(e)}',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


@router.post(
    '/{booking_id}/test-notification',
    responses={
        status.HTTP_200_OK: {'model': dict},
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def test_booking_notification(
    booking_id: UUID,
    session: DbSession,
    notification_type: str = Query(
        'created',
        description='Тип уведомления: created/updated/reminder',
    ),
) -> dict:
    """Тестовый эндпоинт для проверки уведомлений о бронировании."""
    try:
        booking = await booking_repository.get_with_relations(
            session,
            booking_id,
        )
        if not booking:
            logger.warning(
                f'Бронирование {booking_id} не найдено для теста уведомления',
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Бронирование не найдено',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        user_stmt = select(User).limit(1)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if notification_type == 'created':
            await NotificationService.send_booking_created_notification(
                session,
                booking_id,
                user.id if user else None,
            )
        elif notification_type == 'updated':
            await NotificationService.send_booking_updated_notification(
                session,
                booking_id,
                user.id if user else None,
            )
        elif notification_type == 'reminder':
            await NotificationService.send_booking_reminder(
                session,
                booking_id,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=build_error(
                    'Неизвестный тип уведомления',
                    status.HTTP_400_BAD_REQUEST,
                ),
            )
        return {'status': 'success', 'message': 'Уведомление отправлено'}
    except ValueError as e:
        logger.error(f'Ошибка валидации при тесте уведомления: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_error(str(e), status.HTTP_400_BAD_REQUEST),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Ошибка тестирования уведомления: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                f'Ошибка отправки уведомления: {str(e)}',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )
