import io
import os
import uuid
from typing import Annotated

import aiofiles
import anyio
from PIL import Image
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse

from app.core.auth import role_checker
from app.core.constants import (
    ALLOWED_IMAGE_EXTENSIONS,
    JPEG_QUALITY,
    MAX_IMAGE_FILE_SIZE,
    MEDIA_DIR,
)
from app.core.db import DbSession
from app.models.media import Media
from app.models.user import User
from app.schemas.media import CustomError, MediaInfo
from app.utils.enums import UserRole

router = APIRouter(prefix='/media', tags=['Медиа'])


def validate_image_file(file: UploadFile) -> None:
    """Validate uploaded image file."""
    # Check file extension
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail=CustomError(
                code=400,
                message='Имя файла не указано',
            ).dict(),
        )

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=CustomError(
                code=400,
                message=(
                    f'Неподдерживаемый формат файла. '
                    f'Разрешены: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}'
                ),
            ).dict(),
        )

    # Check file size
    if file.size and file.size > MAX_IMAGE_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=CustomError(
                code=400,
                message='Размер файла превышает максимально допустимый (5MB)',
            ).dict(),
        )


def convert_to_jpg(image_data: bytes) -> bytes:
    """Convert image to JPG format."""
    try:
        image = Image.open(io.BytesIO(image_data))

        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            mask = image.split()[-1] if image.mode == 'RGBA' else None
            background.paste(image, mask=mask)
            image = background

        # Save as JPG
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=JPEG_QUALITY)
        return output.getvalue()
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=CustomError(
                code=422,
                message=f'Ошибка обработки изображения: {str(e)}',
            ).dict(),
        )


@router.post(
    '',
    response_model=MediaInfo,
    responses={
        400: {
            'model': CustomError,
            'description': 'Ошибка в параметрах запроса',
        },
        401: {
            'model': CustomError,
            'description': 'Неавторизированный пользователь',
        },
        403: {'model': CustomError, 'description': 'Доступ запрещен'},
        422: {'model': CustomError, 'description': 'Ошибка сохранения файла'},
    },
    summary='Загрузка изображения',
    description=(
        'Загрузка изображения на сервер. Поддерживаются форматы jpg, png. '
        'Размер файла не более 5Мб. Только для администраторов и менеджеров'
    ),
)
async def upload_media(
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(role_checker([UserRole.MANAGER, UserRole.ADMIN])),
    ],
    file: UploadFile = File(...),
) -> MediaInfo:
    """Upload image file (admin and manager only)."""
    # Validate file
    validate_image_file(file)

    try:
        # Read file content
        file_content = await file.read()

        # Convert to JPG
        jpg_content = convert_to_jpg(file_content)

        # Generate UUID4 for the image
        media_id = uuid.uuid4()

        # Create media directory if it doesn't exist
        os.makedirs(MEDIA_DIR, exist_ok=True)

        # Create file path with UUID as filename
        file_path = os.path.join(MEDIA_DIR, f'{media_id}.jpg')

        # Save file to disk using async file operations
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(jpg_content)

        # Save to database with file path
        media_record = Media(
            id=media_id,
            filename=file.filename or 'unknown.jpg',
            content_type='image/jpeg',
            file_size=len(jpg_content),
            file_path=file_path,
        )

        session.add(media_record)
        await session.commit()
        await session.refresh(media_record)

        return MediaInfo(media_id=media_record.id)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=422,
            detail=CustomError(
                code=422,
                message=f'Ошибка сохранения файла: {str(e)}',
            ).dict(),
        )


@router.get(
    '/{media_id}',
    responses={
        200: {
            'description': (
                'Успешно. Возвращает изображение в бинарном формате'
            ),
        },
        404: {'model': CustomError, 'description': 'Данные не найдены'},
        422: {'model': CustomError, 'description': 'Ошибка валидации данных'},
    },
    summary='Возвращает изображение в бинарном формате',
)
async def get_media(
    media_id: uuid.UUID,
    session: DbSession,
) -> FileResponse:
    """Get image by ID (available to all users)."""
    # Find media record in database
    media_record = await session.get(Media, media_id)

    if not media_record:
        raise HTTPException(
            status_code=404,
            detail=CustomError(
                code=404,
                message='Изображение не найдено',
            ).dict(),
        )

    # Check if file exists on disk
    if not await anyio.Path(media_record.file_path).exists():
        raise HTTPException(
            status_code=404,
            detail=CustomError(
                code=404,
                message='Файл изображения не найден на диске',
            ).dict(),
        )

    # Return file as response
    return FileResponse(
        path=media_record.file_path,
        media_type=media_record.content_type,
        filename=f'{media_id}.jpg',
    )
