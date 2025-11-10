from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_password_hash
from app.core.config import settings
from app.repositories.user import user_repository
from app.schemas.user import UserCreate
from app.utils.enums import UserRole


async def upsert_admin_if_not_exist(session: AsyncSession) -> None:
    """Проверяет наличие дефолтной учётки. Воссоздаёт при необходимости."""
    admin_user = UserCreate(
        username=settings.ADMIN_USERNAME,
        email=settings.ADMIN_EMAIL,
        phone=settings.ADMIN_PHONE,
        tg_id=settings.ADMIN_TG_ID,
        password=settings.ADMIN_PASSWORD,
    )

    existing_user = await user_repository.get_by_credentials(
        session,
        admin_user,
    )

    if existing_user:
        existing_user.username = admin_user.username
        existing_user.email = admin_user.email
        existing_user.phone = admin_user.phone
        existing_user.tg_id = admin_user.tg_id
        existing_user.hashed_password = get_password_hash(admin_user.password)
        existing_user.role = UserRole.ADMIN
        existing_user.is_active = True
        await session.commit()

    else:
        # Если пользователь не найден, создаём нового с ролью администратора
        new_user = UserCreate(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            phone=settings.ADMIN_PHONE,
            tg_id=settings.ADMIN_TG_ID,
            password=settings.ADMIN_PASSWORD,
            role=UserRole.ADMIN,
        )
        await user_repository.create(session, obj_in=new_user)
