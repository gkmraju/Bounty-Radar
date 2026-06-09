from __future__ import annotations

from bounty_radar_telegram.models import Bounty
from bounty_radar_telegram.services.ranking import RankingService


def test_ranking_uses_weighted_formula(settings):
    bounty = Bounty(
        id="rank-1",
        title="Python API bounty",
        platform="github",
        url="https://example.com/issues/1",
        prize_min=1000,
        prize_max=5000,
        currency="USD",
        category="oss-bounty",
        skills=["python", "api"],
        difficulty="intermediate",
        freshness_date="2026-06-08T00:00:00+00:00",
        trust_score=80.0,
        description="A fresh Python API bounty.",
        scope_summary="Add a documented API feature.",
    )

    ranking = RankingService(settings, db=None).rank_bounty(bounty)
    expected = (
        ranking.prize_score * 0.35
        + ranking.difficulty_fit_score * 0.25
        + ranking.freshness_score * 0.15
        + ranking.trust_score * 0.15
        + ranking.competition_score * 0.10
    )

    assert ranking.score == round(expected, 2)
    assert ranking.difficulty_fit_score > 80
    assert ranking.score > 70
