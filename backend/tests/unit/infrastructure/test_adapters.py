import io
import os
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from studlenta.domain.errors import AuthenticationError
from studlenta.domain.users import Role, User
from studlenta.infrastructure.files import (
    LocalFileStorage,
    PillowImageInspector,
    cleanup_orphan_covers,
    rebuild_covers,
)
from studlenta.infrastructure.security import Argon2PasswordHasher, JwtTokenService
from studlenta.infrastructure.settings import Settings
from tests.fakes import NOW


def png(width: int, height: int, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "#2B59E0").save(buf, fmt)
    return buf.getvalue()


class TestPasswords:
    def test_hash_is_salted_and_verifiable(self) -> None:
        hasher = Argon2PasswordHasher()
        first, second = hasher.hash("password1"), hasher.hash("password1")
        assert first != second
        assert hasher.verify(first, "password1")
        assert not hasher.verify(first, "password2")
        assert not hasher.verify("not-a-hash", "password1")


class TestJwt:
    @pytest.fixture
    def tokens(self) -> JwtTokenService:
        return JwtTokenService(secret="s" * 32, access_ttl=timedelta(minutes=15))

    def test_roundtrip(self, tokens: JwtTokenService) -> None:
        user = User(uuid4(), "a@uust.ru", "Анна", Role.MODERATOR, "h", NOW)
        actor = tokens.decode_access_token(tokens.issue_access_token(user, NOW), now=NOW)
        assert (actor.user_id, actor.role) == (user.id, Role.MODERATOR)

    def test_expired_and_tampered(self, tokens: JwtTokenService) -> None:
        user = User(uuid4(), "a@uust.ru", "Анна", Role.AUTHOR, "h", NOW)
        token = tokens.issue_access_token(user, NOW)
        with pytest.raises(AuthenticationError):
            tokens.decode_access_token(token, now=NOW + timedelta(minutes=16))
        with pytest.raises(AuthenticationError):
            tokens.decode_access_token(token[:-2] + "xx", now=NOW)
        other = JwtTokenService(secret="o" * 32, access_ttl=timedelta(minutes=15))
        with pytest.raises(AuthenticationError):
            other.decode_access_token(token, now=NOW)

    def test_short_secret_is_refused(self) -> None:
        with pytest.raises(ValueError, match="32"):
            JwtTokenService(secret="short", access_ttl=timedelta(minutes=15))

    def test_refresh_tokens(self, tokens: JwtTokenService) -> None:
        a, b = tokens.new_refresh_token(), tokens.new_refresh_token()
        assert a != b
        assert len(a) >= 40
        assert tokens.hash_refresh_token(a) == tokens.hash_refresh_token(a)
        assert tokens.hash_refresh_token(a) != a


class TestImages:
    @pytest.mark.parametrize(("fmt", "name"), [("PNG", "png"), ("JPEG", "jpeg"), ("WEBP", "webp")])
    def test_detects_format_and_size(self, fmt: str, name: str) -> None:
        info = PillowImageInspector().inspect(png(1300, 700, fmt))
        assert info is not None
        assert (info.format, info.width, info.height) == (name, 1300, 700)

    def test_garbage(self) -> None:
        assert PillowImageInspector().inspect(b"<svg onload=alert(1)>") is None


class TestStorage:
    async def test_saves_under_root_and_returns_url(self, tmp_path: Path) -> None:
        storage = LocalFileStorage(tmp_path, "/media")
        url = await storage.save("covers/a.png", b"data")
        assert url == "/media/covers/a.png"
        assert (tmp_path / "covers" / "a.png").read_bytes() == b"data"

    @pytest.mark.parametrize("name", ["../evil.png", "/etc/passwd", "covers/../../x"])
    async def test_refuses_paths_outside_root(self, tmp_path: Path, name: str) -> None:
        with pytest.raises(ValueError, match="outside"):
            await LocalFileStorage(tmp_path / "media", "/media").save(name, b"x")


class TestSettings:
    def test_env_values_and_comma_separated_origins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUDLENTA_JWT_SECRET", "s" * 32)
        monkeypatch.setenv("STUDLENTA_CORS_ORIGINS", "http://a.test, https://b.test")
        monkeypatch.setenv("STUDLENTA_ACCESS_TTL_MINUTES", "5")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.cors_origins == ["http://a.test", "https://b.test"]
        assert settings.access_ttl == timedelta(minutes=5)
        assert settings.tz.key == "Asia/Yekaterinburg"

    def test_short_jwt_secret_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUDLENTA_JWT_SECRET", "short")
        with pytest.raises(ValueError, match="jwt_secret"):
            Settings(_env_file=None)  # type: ignore[call-arg]


class TestCoverProcessing:
    def test_resizes_rotates_and_strips_metadata(self) -> None:
        # Фото «с телефона»: 2400×1350, повёрнуто EXIF-тегом и с GPS-координатами внутри
        exif = Image.Exif()
        exif[0x0112] = 6  # Orientation: повернуть на 90°
        exif[0x0110] = "Pixel 7"  # модель телефона
        gps = exif.get_ifd(0x8825)
        gps[1], gps[2] = "N", (54.0, 44.0, 0.0)  # широта Уфы
        buf = io.BytesIO()
        Image.new("RGB", (2400, 1350), "#7C3AED").save(buf, "JPEG", exif=exif, quality=95)
        original = buf.getvalue()
        assert Image.open(io.BytesIO(original)).getexif().get_ifd(0x8825)  # GPS действительно есть

        images = PillowImageInspector()
        big = Image.open(io.BytesIO(images.to_jpeg(original, 1600)))
        small = Image.open(io.BytesIO(images.to_jpeg(original, 640)))

        assert big.format == "JPEG"
        assert (big.width, big.height) == (1350, 2400)  # поворот применён; уже 1600 — не трогаем
        assert small.width == 640
        assert not big.getexif()  # GPS и прочие метаданные удалены
        assert not small.getexif()

    def test_wide_images_are_limited_to_max_width(self) -> None:
        jpeg = PillowImageInspector().to_jpeg(png(3000, 1500, "PNG"), 1600)
        out = Image.open(io.BytesIO(jpeg))
        assert out.size == (1600, 800)
        assert len(jpeg) < len(png(3000, 1500, "PNG"))


class TestRebuildCovers:
    def test_shrinks_originals_and_adds_thumbnails_once(self, tmp_path: Path) -> None:
        covers = tmp_path / "covers"
        covers.mkdir()
        (covers / "old.jpg").write_bytes(png(1920, 1080, "JPEG"))
        assert rebuild_covers(tmp_path, PillowImageInspector()) == 1
        assert Image.open(covers / "old.jpg").width == 1600
        assert Image.open(covers / "old-640.jpg").width == 640
        assert rebuild_covers(tmp_path, PillowImageInspector()) == 0  # повторный запуск — ничего


class TestOrphanCovers:
    def test_removes_only_old_unreferenced_pairs(self, tmp_path: Path) -> None:
        covers = tmp_path / "covers"
        covers.mkdir()
        for name in ("used", "orphan", "fresh"):
            (covers / f"{name}.jpg").write_bytes(b"x")
            (covers / f"{name}-640.jpg").write_bytes(b"x")
        day_ago = time.time() - 2 * 86_400
        for name in ("used", "orphan"):
            for suffix in ("", "-640"):
                os.utime(covers / f"{name}{suffix}.jpg", (day_ago, day_ago))

        removed = cleanup_orphan_covers(tmp_path, {"used"}, older_than_seconds=86_400)

        assert removed == ["orphan"]
        assert sorted(p.name for p in covers.iterdir()) == [
            "fresh-640.jpg",
            "fresh.jpg",
            "used-640.jpg",
            "used.jpg",
        ]
