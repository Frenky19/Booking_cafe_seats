from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status

from app.core.auth import (
    get_current_user,
    public_or_role_checker,
    role_checker,
)
from app.core.db import DbSession
from app.models.user import User
from app.repositories.user import user_repository
from app.schemas.common import ErrorResponse
from app.schemas.user import UserCreate, UserInfo, UserUpdate, UserUpdateMe
from app.utils.enums import UserRole
from app.utils.http import build_error
from app.utils.logging_decorator import event_logger

router = APIRouter(prefix='/users', tags=['Пользователи'])


@router.get(
    '/',
    response_model=List[UserInfo],
    responses={
        status.HTTP_401_UNAUTHORIZED: {'model': ErrorResponse},
        status.HTTP_403_FORBIDDEN: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_all_users(
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(role_checker([UserRole.MANAGER, UserRole.ADMIN])),
    ],
    show_all: bool = Query(
        False,
        description='Показывать всех пользователей?',
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> List[UserInfo]:
    """Получение списка пользователей."""
    return await user_repository.get_multi(
        session,
        show_all=show_all,
        skip=skip,
        limit=limit,
    )


@router.post(
    '/',
    response_model=UserInfo,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_403_FORBIDDEN: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Создана', 'User')
async def create_user(
    user_data: UserCreate,
    session: DbSession,
    current_user: Optional[User] = Security(
        public_or_role_checker([UserRole.MANAGER, UserRole.ADMIN]),
    ),
) -> UserInfo:
    """Создание нового пользователя.

    Доступно:
    - Неавторизованным пользователям (публичная регистрация)
    - Авторизованным менеджерам и администраторам

    Недоступно:
    - Авторизованным пользователям с ролью USER
    """
    if current_user is not None and current_user.role == UserRole.USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=build_error(
                'Пользователям с ролью USER действие запрещено',
                status.HTTP_403_FORBIDDEN,
            ),
        )

    try:
        return await user_repository.create(session, user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_error(str(e), status.HTTP_400_BAD_REQUEST),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при создании пользователя',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        ) from e


@router.get(
    '/me',
    response_model=UserInfo,
    responses={
        status.HTTP_401_UNAUTHORIZED: {'model': ErrorResponse},
    },
)
async def get_me(
    current_user: Annotated[
        User,
        Depends(
            role_checker([
                UserRole.USER,
                UserRole.MANAGER,
                UserRole.ADMIN,
            ]),
        ),
    ],
) -> UserInfo:
    """Эндпоинт для получения информации о собсвтвенном аккаунте."""
    return current_user


@router.patch(
    '/me',
    response_model=UserInfo,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Обновлена', 'User')
async def update_me(
    update_data: UserUpdateMe,
    session: DbSession,
    current_user: User = Depends(get_current_user),
) -> UserInfo:
    """Обновление информации о текущем пользователе."""
    try:
        return await user_repository.update(
            session,
            current_user,
            update_data,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_error(str(e), status.HTTP_400_BAD_REQUEST),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при обновлении пользователя',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        ) from e


@router.get(
    '/{user_id}',
    response_model=UserInfo,
    responses={
        status.HTTP_401_UNAUTHORIZED: {'model': ErrorResponse},
        status.HTTP_403_FORBIDDEN: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
async def get_user_by_id(
    user_id: UUID,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(role_checker([UserRole.MANAGER, UserRole.ADMIN])),
    ],
) -> UserInfo:
    """Получение информации о пользователе по ID."""
    try:
        user = await user_repository.get(session, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Пользователь не найден',
                    status.HTTP_404_NOT_FOUND,
                ),
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при получении пользователя',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        ) from e


@router.patch(
    '/{user_id}',
    response_model=UserInfo,
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {'model': ErrorResponse},
        status.HTTP_403_FORBIDDEN: {'model': ErrorResponse},
        status.HTTP_404_NOT_FOUND: {'model': ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'model': ErrorResponse},
    },
)
@event_logger('Обновлена', 'User')
async def update_user(
    user_id: UUID,
    update_data: UserUpdate,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(role_checker([UserRole.MANAGER, UserRole.ADMIN])),
    ],
) -> UserInfo:
    """Обновление информации о пользователе по ID."""
    try:
        user = await user_repository.get(session, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=build_error(
                    'Пользователь не найден',
                    status.HTTP_404_NOT_FOUND,
                ),
            )

        if (
            update_data.is_active is not None
            and current_user.role == UserRole.MANAGER
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=build_error(
                    'Недостаточно прав для изменения статуса пользователя',
                    status.HTTP_403_FORBIDDEN,
                ),
            )

        return await user_repository.update(session, user, update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_error(str(e), status.HTTP_400_BAD_REQUEST),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                'Внутренняя ошибка сервера при обновлении пользователя',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        ) from e
