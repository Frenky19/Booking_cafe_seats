from uuid import UUID

from fastapi import File, UploadFile
from pydantic import BaseModel, ConfigDict


class MediaData(BaseModel):
    """Схема для загрузки изображения."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    file: UploadFile = File(
        ...,
        description='Файл изображения (JPG, PNG). Максимальный размер: 5MB',
    )


class MediaInfo(BaseModel):
    """Схема информации о загруженном изображении."""

    media_id: UUID


class CustomError(BaseModel):
    """Схема для возврата ошибок."""

    code: int
    message: str
