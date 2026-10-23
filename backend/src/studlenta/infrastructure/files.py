"""Файлы обложек: локальный диск (на хакатоне хватает) и проверка картинок через Pillow."""

import asyncio
import io
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from studlenta.application.dto import ImageInfo

_FORMATS = {"JPEG": "jpeg", "PNG": "png", "WEBP": "webp"}


class LocalFileStorage:
    def __init__(self, root: Path, base_url: str) -> None:
        self._root = root.resolve()
        self._base_url = base_url.rstrip("/")

    async def save(self, name: str, data: bytes) -> str:
        target = (self._root / name).resolve()
        if not target.is_relative_to(self._root):
            raise ValueError("path is outside of storage root")

        def write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

        await asyncio.to_thread(write)
        return f"{self._base_url}/{target.relative_to(self._root).as_posix()}"


class PillowImageInspector:
    def inspect(self, data: bytes) -> ImageInfo | None:
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
                fmt = _FORMATS.get(image.format or "")
                return ImageInfo(fmt, image.width, image.height) if fmt else None
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
            return None
