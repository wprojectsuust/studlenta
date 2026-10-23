"""Файлы обложек: локальный диск (на хакатоне хватает) и проверка картинок через Pillow."""

import asyncio
import io
import time
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

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

    def to_jpeg(self, data: bytes, max_width: int) -> bytes:
        with Image.open(io.BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source)
            if image.mode in ("RGBA", "LA", "P"):
                image = image.convert("RGBA")
                background = Image.new("RGB", image.size, "#FFFFFF")
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            if image.width > max_width:
                height = round(image.height * max_width / image.width)
                image = image.resize((max_width, height), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            # Без exif=… Pillow метаданные не пишет — GPS и модель телефона не утекут.
            image.save(out, "JPEG", quality=82, optimize=True, progressive=True)
            return out.getvalue()


def rebuild_covers(media_root: Path, images: PillowImageInspector) -> int:
    """Обложки, загруженные до появления превью: пересжать и добавить ``-640``. Идемпотентно."""
    done = 0
    for path in sorted((media_root / "covers").glob("*.jpg")):
        if path.stem.endswith("-640"):
            continue
        thumb = path.with_name(f"{path.stem}-640.jpg")
        if thumb.exists():
            continue
        data = path.read_bytes()
        path.write_bytes(images.to_jpeg(data, 1600))
        thumb.write_bytes(images.to_jpeg(data, 640))
        done += 1
    return done


def cleanup_orphan_covers(
    media_root: Path, referenced: set[str], older_than_seconds: float = 86_400
) -> list[str]:
    """Удаляет обложки, на которые не ссылается ни одно событие и которые старше суток.

    Порог возраста — чтобы не удалить обложку, загруженную только что для ещё не сохранённого
    черновика. ``referenced`` — имена файлов без расширения.
    """
    removed: list[str] = []
    cutoff = time.time() - older_than_seconds
    for path in sorted((media_root / "covers").glob("*.jpg")):
        stem = path.stem
        if stem.endswith("-640") or stem in referenced or path.stat().st_mtime > cutoff:
            continue
        path.unlink()
        path.with_name(f"{stem}-640.jpg").unlink(missing_ok=True)
        removed.append(stem)
    return removed
