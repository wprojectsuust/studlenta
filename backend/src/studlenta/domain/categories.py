import re
from dataclasses import dataclass

from studlenta.domain.errors import ValidationError

# Заливки тегов. Белый текст на каждой даёт контраст ≥ 4.5:1 (WCAG 2.1 AA),
# поэтому произвольные цвета категориям запрещены.
CATEGORY_PALETTE = frozenset(
    {"#7C3AED", "#15803D", "#1D4ED8", "#C2410C", "#BE185D", "#0E7490", "#4B5563"}
)
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


@dataclass(frozen=True, slots=True)
class Category:
    id: int
    slug: str
    name: str
    color: str

    @classmethod
    def create(cls, *, category_id: int, slug: str, name: str, color: str) -> "Category":
        errors: dict[str, str] = {}
        if not _SLUG.match(slug):
            errors["slug"] = "Только латиница в нижнем регистре, цифры и дефис"
        name = name.strip()
        if not name:
            errors["name"] = "Укажите название"
        color = color.upper()
        if color not in CATEGORY_PALETTE:
            errors["color"] = "Цвет должен быть из палитры"
        if errors:
            raise ValidationError(errors)
        return cls(id=category_id, slug=slug, name=name, color=color)
