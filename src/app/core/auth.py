from datetime import datetime, timedelta, timezone
from typing import Annotated, Awaitable, Callable, List, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from app.core.config import settings
from app.core.db import DbSession
from app.core.logging import logger
from app.models.user import User
from app.utils.enums import UserRole

# Для обязательной аутентификации
security = HTTPBearer(auto_error=False)

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def get_token_expires() -> timedelta:
    """Возвращает время жизни токена."""
    return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Хеширование пароля."""
    return pwd_context.hash(password)


def create_access_token(user_id: UUID, username: str) -> str:
    """Создает JWT токен."""
    expire = datetime.now(timezone.utc) + get_token_expires()

    to_encode = {
        'sub': str(user_id),
        'username': username,
        'exp': expire,
    }

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


async def get_current_user_optional(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(security),
    ],
    session: DbSession,
    request: Request = None,
) -> Optional[User]:
    """Получение текущего пользователя из JWT токена (опционально).

    Если токен отсутствует или невалиден, возвращает None.
    """
    if request:
        logger.info(f'Заголовки запроса: {dict(request.headers)}')
    if credentials is None:
        logger.info('Отсутствует заголовок Authorization в headers')
        return None
    token = credentials.credentials
    logger.info(f'Получен: {token}')

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get('sub')

        if user_id is None:
            return None

        stmt = select(User).where(
            User.id == UUID(user_id),
            User.is_active.is_(True),
        )
        result = await session.execute(stmt)

        return result.scalar_one_or_none()

    except JWTError as e:
        logger.warning(f'JWTError при обработке токена: {e}')
        return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: DbSession,
    request: Request = None,
) -> User:
    """Получение текущего пользователя из JWT токена."""
    if request:
        logger.info(f'Заголовки запроса: {request.headers}')
    if credentials is None:
        logger.info('Отсутствует заголовок Authorization в headers')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Не авторизован',
        )

    token = credentials.credentials
    logger.info(f'Получен токен: {token}')

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get('sub')

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Неверные учетные данные',
            )

        stmt = select(User).where(
            User.id == UUID(user_id),
            User.is_active.is_(True),
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Пользователь не найден или неактивен',
            )

        return user

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверные учетные данные',
        )


def public_or_role_checker(
    allowed_roles: List[UserRole],
) -> Callable[..., Awaitable[Optional[User]]]:
    """Проверка роли или ее отсутсвия для публичных эндпоинтов."""

    async def checker(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(
            security,
        ),
        session: DbSession = Depends,
    ) -> Optional[User]:
        current_user = await get_current_user_optional(credentials, session)
        if current_user is None:
            return None
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Недостаточно прав для выполнения операции',
            )
        return current_user

    return checker


def role_checker(allowed_roles: List[UserRole]) -> User:
    """Универсальная функция для проверки ролей пользователя."""

    async def checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        # Проверяем, есть ли у пользователя нужная роль
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Недостаточно прав для выполнения операции',
            )

        return current_user

    return checker
