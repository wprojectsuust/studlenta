"""Сценарий: автор загружает обложку события."""

import asyncio

from studlenta.application.dto import Actor
from studlenta.application.ports import FileStorage, IdGenerator, ImageInspector
from studlenta.domain.errors import ValidationError

MAX_COVER_BYTES = 5 * 1024 * 1024
MIN_COVER_WIDTH = 1200
COVER_WIDTH = 1600  # страница события
THUMB_WIDTH = 640  # карточка в ленте — та же картинка в разы легче
_FORMATS = {"jpeg", "png", "webp"}


class UploadCover:
    def __init__(self, storage: FileStorage, inspector: ImageInspector, ids: IdGenerator) -> None:
        self._storage, self._inspector, self._ids = storage, inspector, ids

    async def __call__(self, actor: Actor, data: bytes) -> str:
        if len(data) > MAX_COVER_BYTES:
            raise ValidationError({"cover": "Файл больше 5 МБ"})
        info = self._inspector.inspect(data)
        if info is None or info.format not in _FORMATS:
            raise ValidationError({"cover": "Нужна картинка JPG, PNG или WEBP"})
        if info.width < MIN_COVER_WIDTH:
            raise ValidationError({"cover": f"Нужна картинка шириной от {MIN_COVER_WIDTH} px"})
        # Сохраняем не исходник: пересжатая копия легче и без EXIF (там бывают координаты).
        cover = await asyncio.to_thread(self._inspector.to_jpeg, data, COVER_WIDTH)
        thumb = await asyncio.to_thread(self._inspector.to_jpeg, data, THUMB_WIDTH)
        name = f"covers/{self._ids.new_id()}"
        await self._storage.save(f"{name}-{THUMB_WIDTH}.jpg", thumb)
        return await self._storage.save(f"{name}.jpg", cover)
