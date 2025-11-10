from fastapi import APIRouter, HTTPException, status

from app.core.auth import create_access_token, verify_password
from app.core.db import DbSession
from app.repositories.user import user_repository
from app.schemas.auth import AuthData, AuthToken

router = APIRouter(prefix='/auth', tags=['Аутентификация'])


@router.post('/login', response_model=AuthToken)
async def login(
    session: DbSession,
    login_data: AuthData,
) -> AuthToken:
    """Аутентификация пользователя и получение JWT токена."""
    user = await user_repository.get_by_login(session, login_data.login)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверный логин или пароль',
        )

    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверный логин или пароль',
        )

    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
    )

    return AuthToken(access_token=access_token, token_type='bearer')
