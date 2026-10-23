from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from studlenta.domain.recommendations import (
    Candidate,
    CoView,
    Interaction,
    ReasonKind,
    decay,
    recommend,
)

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
CONCERTS, SPORT, SCIENCE = 1, 2, 3


def eid(n: int) -> UUID:
    return UUID(int=n)


def seen(n: int, category: int, words: str, kind: str = "view", days_ago: float = 0) -> Interaction:
    return Interaction(
        eid(n), category, frozenset(words.split()), kind, NOW - timedelta(days=days_ago)
    )


def cand(n: int, category: int, words: str, popularity: float = 0) -> Candidate:
    return Candidate(eid(n), category, frozenset(words.split()), popularity)


class TestDecay:
    def test_halves_every_two_weeks(self) -> None:
        assert decay(NOW, NOW) == 1
        assert decay(NOW - timedelta(days=14), NOW) == pytest.approx(0.5)
        assert decay(NOW - timedelta(days=28), NOW) == pytest.approx(0.25)

    def test_future_timestamps_do_not_inflate(self) -> None:
        assert decay(NOW + timedelta(days=3), NOW) == 1


class TestColdStart:
    def test_without_history_most_popular_go_first(self) -> None:
        recs = recommend([], [cand(10, SPORT, "футбол", 1), cand(11, SPORT, "шахматы", 9)], [], NOW)
        assert [r.event_id for r in recs] == [eid(11), eid(10)]
        assert recs[0].reason.kind is ReasonKind.POPULAR

    def test_nothing_popular_yet_keeps_order_by_date(self) -> None:
        recs = recommend([], [cand(10, SPORT, "футбол"), cand(11, SPORT, "шахматы")], [], NOW)
        assert [r.event_id for r in recs] == [eid(10), eid(11)]
        assert all(r.reason.kind is ReasonKind.SOON for r in recs)


class TestPersonal:
    def test_favourite_category_wins_and_is_explained(self) -> None:
        history = [seen(1, CONCERTS, "джаз вечер", "favorite"), seen(2, CONCERTS, "рок")]
        pool = [cand(10, SPORT, "футбол", popularity=5), cand(11, CONCERTS, "хор")]
        recs = recommend(history, pool, [], NOW)
        assert recs[0].event_id == eid(11)
        assert recs[0].reason.kind is ReasonKind.CATEGORY
        assert recs[0].reason.ref == CONCERTS

    def test_similar_words_point_to_the_closest_seen_event(self) -> None:
        history = [seen(1, SCIENCE, "хакатон python команда"), seen(2, SPORT, "забег парк")]
        pool = [cand(10, CONCERTS, "хакатон python"), cand(11, CONCERTS, "балет")]
        recs = recommend(history, pool, [], NOW)
        assert recs[0].event_id == eid(10)
        assert recs[0].reason.kind is ReasonKind.SIMILAR
        assert recs[0].reason.ref == eid(1)

    def test_people_who_viewed_the_same_also_viewed(self) -> None:
        history = [seen(1, SCIENCE, "лекция")]
        pool = [cand(10, CONCERTS, "балет"), cand(11, SPORT, "футбол")]
        recs = recommend(history, pool, [CoView(eid(11), eid(1), viewers=4)], NOW)
        assert recs[0].event_id == eid(11)
        assert recs[0].reason.kind is ReasonKind.ALSO_VIEWED
        assert recs[0].reason.ref == eid(1)

    def test_fresh_interest_outweighs_old_one(self) -> None:
        history = [
            seen(1, SPORT, "футбол", "favorite", days_ago=60),
            seen(2, CONCERTS, "джаз", "favorite", days_ago=1),
        ]
        recs = recommend(history, [cand(10, SPORT, "волейбол"), cand(11, CONCERTS, "хор")], [], NOW)
        assert recs[0].event_id == eid(11)

    def test_already_seen_events_are_not_recommended(self) -> None:
        history = [seen(1, CONCERTS, "джаз")]
        recs = recommend(history, [cand(1, CONCERTS, "джаз"), cand(10, CONCERTS, "хор")], [], NOW)
        assert [r.event_id for r in recs] == [eid(10)]

    def test_limit_and_scores_are_sorted(self) -> None:
        history = [seen(1, CONCERTS, "джаз")]
        pool = [cand(n, CONCERTS if n % 2 else SPORT, f"слово{n}", n) for n in range(10, 30)]
        recs = recommend(history, pool, [], NOW, limit=5)
        assert len(recs) == 5
        assert [r.score for r in recs] == sorted((r.score for r in recs), reverse=True)
