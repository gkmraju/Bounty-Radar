from __future__ import annotations

from bounty_radar_telegram.config import Settings
from bounty_radar_telegram.db import Database
from bounty_radar_telegram.models import Bounty, RankBreakdown
from bounty_radar_telegram.utils import (
    competition_score,
    difficulty_fit_score,
    freshness_score,
    prize_score,
)


class RankingService:
    def __init__(self, settings: Settings, db: Database) -> None:
        self.settings = settings
        self.db = db

    def run(self) -> list[RankBreakdown]:
        rankings = [self.rank_bounty(bounty) for bounty in self.db.list_bounties()]
        self.db.update_rankings(rankings)
        return rankings

    def rank_bounty(self, bounty: Bounty) -> RankBreakdown:
        prize_component = prize_score(bounty.prize_min, bounty.prize_max)
        difficulty_component = difficulty_fit_score(
            bounty.difficulty,
            bounty.skills,
            self.settings.skill_filters,
        )
        freshness_component = freshness_score(bounty.freshness_date)
        competition_component = competition_score(
            bounty.platform,
            bounty.category,
            bounty.skills,
            bounty.description,
        )
        total = (
            prize_component * 0.35
            + difficulty_component * 0.25
            + freshness_component * 0.15
            + bounty.trust_score * 0.15
            + competition_component * 0.10
        )
        return RankBreakdown(
            bounty_id=bounty.id,
            prize_score=round(prize_component, 2),
            difficulty_fit_score=round(difficulty_component, 2),
            freshness_score=round(freshness_component, 2),
            trust_score=round(bounty.trust_score, 2),
            competition_score=round(competition_component, 2),
            score=round(total, 2),
        )
