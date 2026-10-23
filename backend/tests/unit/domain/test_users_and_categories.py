from datetime import UTC, datetime
from uuid import uuid4

import pytest

from studlenta.domain.categories import CATEGORY_PALETTE, Category
from studlenta.domain.errors import ValidationError
from studlenta.domain.users import Role, User, normalize_email, validate_password


class TestEmail:
    def test_is_trimmed_and_lowercased(self) -> None:
        assert normalize_email("  Anna.Smirnova@UUST.ru ") == "anna.smirnova@uust.ru"

    @pytest.mark.parametrize("raw", ["", "anna", "anna@", "@uust.ru", "an na@uust.ru", "a@b"])
    def test_rejects_malformed(self, raw: str) -> None:
        with pytest.raises(ValidationError) as exc:
            normalize_email(raw)
        assert "email" in exc.value.fields


class TestPassword:
    def test_eight_characters_is_enough(self) -> None:
        validate_password("12345678")

    @pytest.mark.parametrize("raw", ["", "1234567", "x" * 129])
    def test_rejects_too_short_or_too_long(self, raw: str) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_password(raw)
        assert "password" in exc.value.fields


class TestRoles:
    @pytest.mark.parametrize(
        ("role", "can_moderate"),
        [(Role.AUTHOR, False), (Role.MODERATOR, True), (Role.ADMIN, True)],
    )
    def test_moderation_rights(self, role: Role, can_moderate: bool) -> None:
        assert role.can_moderate is can_moderate


class TestCategory:
    def test_color_must_come_from_accessible_palette(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Category.create(category_id=1, slug="sport", name="Спорт", color="#FFFF00")
        assert "color" in exc.value.fields

    def test_valid_category(self) -> None:
        cat = Category.create(category_id=1, slug="sport", name=" Спорт ", color="#15803D")
        assert cat.name == "Спорт"
        assert cat.color in CATEGORY_PALETTE

    @pytest.mark.parametrize("slug", ["", "Спорт", "sport fans", "-sport"])
    def test_slug_is_url_safe(self, slug: str) -> None:
        with pytest.raises(ValidationError):
            Category.create(category_id=1, slug=slug, name="Спорт", color="#15803D")


class TestVerification:
    def test_user_is_verified_once_email_confirmed(self) -> None:
        now = datetime(2026, 10, 23, tzinfo=UTC)
        user = User(uuid4(), "a@uust.ru", "Анна", Role.AUTHOR, "h", now)
        assert not user.is_verified
        assert user.verified(now).is_verified
        assert user.verified(now).email_verified_at == now
