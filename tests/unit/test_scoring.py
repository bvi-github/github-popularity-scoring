from datetime import datetime, timezone, timedelta

from github_popularity_scoring.domain.entities import Repository
from github_popularity_scoring.domain.scoring import PopularityScorer

def build_repository(stars: int, forks: int, updated_at: datetime) -> Repository:
    return Repository(
        name="demo",
        stars=stars,
        forks=forks,
        updated_at=updated_at,
    )

def test_score_increases_for_more_stars_and_forks() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scorer = PopularityScorer(now_provider=lambda: now)

    smaller_repo = build_repository(
        stars=2,
        forks=3,
        updated_at=now - timedelta(days=7)
    )

    larger_repo = build_repository(
        stars=20,
        forks=30,
        updated_at=now - timedelta(days=7)
    )

    assert scorer.score(larger_repo) > scorer.score(smaller_repo)


def test_score_increases_for_more_recent_update() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scorer = PopularityScorer(now_provider=lambda: now)

    fresh_repo = build_repository(
        stars=2,
        forks=3,
        updated_at=now - timedelta(days=7)
    )

    stale_repo = build_repository(
        stars=2,
        forks=3,
        updated_at=now - timedelta(days=14)
    )

    assert scorer.score(fresh_repo) > scorer.score(stale_repo)