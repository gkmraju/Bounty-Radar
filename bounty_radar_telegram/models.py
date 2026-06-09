from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Bounty:
    id: str
    title: str
    platform: str
    url: str
    prize_min: float | None
    prize_max: float | None
    currency: str
    category: str
    skills: list[str]
    difficulty: str
    freshness_date: str
    trust_score: float
    description: str
    scope_summary: str
    competition_score: float = 50.0
    score: float = 0.0
    prize_score: float = 0.0
    difficulty_fit_score: float = 0.0
    freshness_score: float = 0.0
    dedupe_key: str = ""
    source_id: str = ""
    raw_payload: str = ""
    created_at: str = ""
    updated_at: str = ""

    def searchable_text(self) -> str:
        return " ".join(
            [
                self.title,
                self.platform,
                self.category,
                " ".join(self.skills),
                self.description,
                self.scope_summary,
            ]
        ).lower()

    @property
    def display_prize(self) -> str:
        if self.prize_min is None and self.prize_max is None:
            return "Undisclosed"
        if self.prize_min is not None and self.prize_max is not None:
            if self.prize_min == self.prize_max:
                return f"{self.currency} {self.prize_max:,.0f}"
            return f"{self.currency} {self.prize_min:,.0f}-{self.prize_max:,.0f}"
        value = self.prize_max if self.prize_max is not None else self.prize_min
        return f"{self.currency} {value:,.0f}"


@dataclass(slots=True)
class RankBreakdown:
    bounty_id: str
    prize_score: float
    difficulty_fit_score: float
    freshness_score: float
    trust_score: float
    competition_score: float
    score: float


@dataclass(slots=True)
class PublishResult:
    bounty_id: str
    sent: bool
    message: str
    message_id: str = ""
    preview: str = ""


@dataclass(slots=True)
class FetchStats:
    fetched: int = 0
    stored: int = 0
    duplicates_removed: int = 0
    adapter_errors: list[str] = field(default_factory=list)
