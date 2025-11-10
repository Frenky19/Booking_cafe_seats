from typing import List, Optional, Union
from uuid import UUID

from passlib.context import CryptContext
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_password_hash
from app.models.user import User
from app.repositories.base import CRUDBase
from app.schemas.user import UserCreate, UserUpdate, UserUpdateMe
from app.utils.enums import UserRole

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


class UserRepository(CRUDBase[User, UserCreate, UserUpdate]):
    """Репозиторий для операций с пользователями."""

    def __init__(self) -> None:
        """Инициализация репозитория пользователей."""
        super().__init__(User)

    async def create(
        self,
        session: AsyncSession,
        obj_in: UserCreate,
    ) -> User:
        """Создание пользователя с хешированием пароля."""
        try:
            create_data = obj_in.model_dump(exclude={'password'})
            create_data['hashed_password'] = get_password_hash(obj_in.password)

            # Проверяем уникальность username, email, phone, tg_id
            existing_user = await self.get_by_credentials(session, obj_in)
            if existing_user:
                raise ValueError(
                    'Пользователь с такими данными уже существует',
                )

            db_obj = self.model(**create_data)
            session.add(db_obj)
            await session.commit()
            await session.refresh(db_obj)
        except IntegrityError:
            await session.rollback()
            raise ValueError('Пользователь с такими данными уже существует')

        return db_obj

    async def get_by_credentials(
        self,
        session: AsyncSession,
        user_data: Union[UserCreate, UserUpdate, UserUpdateMe],
        exclude_user_id: Optional[UUID] = None,
    ) -> Optional[User]:
        """Поиск пользователя по учетным данным."""
        conditions = []
        if user_data.username:
            conditions.append(User.username == user_data.username)
        if user_data.email:
            conditions.append(User.email == user_data.email)
        if user_data.phone:
            conditions.append(User.phone == user_data.phone)
        if user_data.tg_id:
            conditions.append(User.tg_id == user_data.tg_id)

        if not conditions:
            return None

        query = select(User).where(or_(*conditions))

        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)

        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def update(
        self,
        session: AsyncSession,
        db_obj: User,
        obj_in: UserUpdate | UserUpdateMe,
    ) -> User:
        """Обновление пользователя."""
        update_data = obj_in.model_dump(exclude_unset=True)

        if isinstance(obj_in, UserUpdateMe) and 'role' in update_data:
            raise ValueError('Нельзя изменять роль через этот эндпоинт')

        conflicting_user = await self.get_by_credentials(
            session,
            user_data=obj_in,
            exclude_user_id=db_obj.id,
        )

        if conflicting_user:
            raise ValueError(
                'Другой пользователь с такими данными уже существует',
            )

        if 'password' in update_data:
            update_data['hashed_password'] = get_password_hash(
                update_data.pop('password'),
            )

        if 'role' in update_data and update_data['role'] is not None:
            role_mapping = {
                0: UserRole.USER,
                1: UserRole.MANAGER,
                2: UserRole.ADMIN,
            }
            update_data['role'] = role_mapping.get(
                update_data['role'],
                UserRole.USER,
            )

        # Проверяем контакты
        if 'phone' in update_data or 'email' in update_data:
            new_phone = update_data.get('phone', db_obj.phone)
            new_email = update_data.get('email', db_obj.email)
            if not new_phone and not new_email:
                raise ValueError('Пользователь должен иметь email или телефон')

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get_multi(
        self,
        session: AsyncSession,
        show_all: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """Получение списка пользователей."""
        conditions = []
        if not show_all:
            conditions.append(User.is_active.is_(True))
        return await self.get(
            session,
            *conditions,
            many=True,
            offset=skip,
            limit=limit,
        )

    async def get_by_email(
        self,
        session: AsyncSession,
        email: str,
    ) -> Optional[User]:
        """Получает пользователя по email."""
        return await self.get(session, email=email)

    async def get_by_phone(
        self,
        session: AsyncSession,
        phone: str,
    ) -> Optional[User]:
        """Получает пользователя по телефону."""
        return await self.get(session, phone=phone)

    async def get_by_login(
        self,
        session: AsyncSession,
        login: str,
    ) -> Optional[User]:
        """Получает пользователя по email или телефону."""
        user = await self.get_by_email(session, login)
        if not user:
            user = await self.get_by_phone(session, login)
        return user


user_repository = UserRepository()
