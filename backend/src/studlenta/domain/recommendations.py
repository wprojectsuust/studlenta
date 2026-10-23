"""Рекомендации «Для вас»: небольшой гибрид без внешних ML-библиотек (ADR-0014).

Профиль интересов строится из просмотров, лайков и избранного с затуханием во времени.
Кандидат получает оценку из четырёх сигналов, и самый весомый из них становится
объяснением, которое видит студент:

* категория — доля интереса к категории кандидата;
* похожесть — косинус TF-IDF по лексемам заголовка и анонса (лексемы даёт PostgreSQL);
* «смотрят вместе» — сколько людей, видевших то же, что и вы, смотрели кандидата;
* популярность — для холодного старта и как слабая добавка.
"""

import math
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

HALF_LIFE_DAYS = 14
KIND_WEIGHT = {"view": 1.0, "like": 3.0, "favorite": 5.0}
WEIGHTS = {"category": 0.4, "similar": 0.3, "also_viewed": 0.2, "popular": 0.1}


class ReasonKind(StrEnum):
    CATEGORY = "category"  # ref — id категории
    SIMILAR = "similar"  # ref — id похожего события из истории
    ALSO_VIEWED = "also_viewed"  # ref — id события из истории
    POPULAR = "popular"
    SOON = "soon"


@dataclass(frozen=True, slots=True)
class Reason:
    kind: ReasonKind
    ref: UUID | int | None = None


@dataclass(frozen=True, slots=True)
class Interaction:
    event_id: UUID
    category_id: int
    lexemes: frozenset[str]
    kind: str  # view | like | favorite
    at: datetime


@dataclass(frozen=True, slots=True)
class Candidate:
    event_id: UUID
    category_id: int
    lexemes: frozenset[str]
    popularity: float


@dataclass(frozen=True, slots=True)
class CoView:
    """Столько людей смотрели и ``seed_id`` из истории, и кандидата ``event_id``."""

    event_id: UUID
    seed_id: UUID
    viewers: int


@dataclass(frozen=True, slots=True)
class Recommendation:
    event_id: UUID
    score: float
    reason: Reason


def decay(at: datetime, now: datetime) -> float:
    age_days = max((now - at).total_seconds() / 86400, 0)
    return float(0.5 ** (age_days / HALF_LIFE_DAYS))


def _idf(docs: Sequence[frozenset[str]]) -> dict[str, float]:
    df = Counter(term for doc in docs for term in doc)
    n = len(docs)
    return {term: math.log((n + 1) / (count + 1)) + 1 for term, count in df.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    dot = sum(w * b.get(t, 0.0) for t, w in a.items())
    norm = math.sqrt(sum(w * w for w in a.values())) * math.sqrt(sum(w * w for w in b.values()))
    return dot / norm if norm else 0.0


def recommend(
    history: Sequence[Interaction],
    candidates: Sequence[Candidate],
    co_views: Sequence[CoView],
    now: datetime,
    limit: int = 10,
) -> list[Recommendation]:
    """Кандидаты приходят по дате начала; при равной оценке порядок сохраняется."""
    seen = {i.event_id for i in history}
    pool = [c for c in candidates if c.event_id not in seen]
    max_pop = max((c.popularity for c in pool), default=0.0)

    weights = {i: KIND_WEIGHT.get(i.kind, 1.0) * decay(i.at, now) for i in history}
    total = sum(weights.values())
    category_interest: defaultdict[int, float] = defaultdict(float)
    for i, w in weights.items():
        category_interest[i.category_id] += w / total

    idf = _idf([c.lexemes for c in pool] + [i.lexemes for i in history])
    profile: defaultdict[str, float] = defaultdict(float)
    for i, w in weights.items():
        for term in i.lexemes:
            profile[term] += w * idf[term]

    best_co: dict[UUID, CoView] = {}
    for pair in co_views:
        if pair.event_id not in best_co or pair.viewers > best_co[pair.event_id].viewers:
            best_co[pair.event_id] = pair
    max_co = max((co.viewers for co in best_co.values()), default=0)

    out = []
    for c in pool:
        vector = {t: idf[t] for t in c.lexemes}
        co = best_co.get(c.event_id)
        parts = {
            "category": WEIGHTS["category"] * category_interest.get(c.category_id, 0.0),
            "similar": WEIGHTS["similar"] * _cosine(dict(profile), vector),
            "also_viewed": WEIGHTS["also_viewed"] * (co.viewers / max_co if co else 0.0),
            "popular": WEIGHTS["popular"] * (c.popularity / max_pop if max_pop else 0.0),
        }
        out.append(Recommendation(c.event_id, sum(parts.values()), _reason(parts, c, co, history)))
    out.sort(key=lambda r: r.score, reverse=True)
    return out[:limit]


def _reason(
    parts: dict[str, float], c: Candidate, co: CoView | None, history: Sequence[Interaction]
) -> Reason:
    top = max(parts, key=lambda k: parts[k])
    if parts[top] == 0:
        return Reason(ReasonKind.SOON)
    if top == "category":
        return Reason(ReasonKind.CATEGORY, c.category_id)
    if top == "similar":
        closest = max(history, key=lambda i: len(i.lexemes & c.lexemes))
        return Reason(ReasonKind.SIMILAR, closest.event_id)
    if top == "also_viewed" and co:
        return Reason(ReasonKind.ALSO_VIEWED, co.seed_id)
    return Reason(ReasonKind.POPULAR)
