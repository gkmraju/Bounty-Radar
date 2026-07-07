from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _split_csv(value: str | None, delimiter: str = ",") -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(delimiter) if item.strip()]


@dataclass(slots=True)
class Settings:
    telegram_bot_token: str
    telegram_channel_id: str
    max_results_per_run: int
    min_score: float
    skill_filters: list[str]
    blocked_keywords: list[str]
    database_path: Path
    github_token: str
    github_queries: list[str]
    rss_sources: list[str]
    manual_json_sources: list[str]
    algora_sources: list[str]
    immunefi_source: str
    hackerone_source: str
    bugcrowd_source: str
    yeswehack_source: str
    request_timeout_seconds: int


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        # A blank env value should disable a source; defaults only apply when the variable is unset.
        telegram_bot_token=(
            os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN", "")
        ).strip(),
        telegram_channel_id=(
            os.getenv("TELEGRAM_CHANNEL_ID") or os.getenv("TELEGRAM_CHAT_ID", "")
        ).strip(),
        max_results_per_run=int(os.getenv("MAX_RESULTS_PER_RUN", "3")),
        min_score=float(os.getenv("MIN_SCORE", "70")),
        skill_filters=[item.lower() for item in _split_csv(os.getenv("SKILL_FILTERS"))],
        blocked_keywords=[item.lower() for item in _split_csv(os.getenv("BLOCKED_KEYWORDS"))],
        database_path=Path(os.getenv("DATABASE_PATH", "bounty_radar.db")),
        github_token=os.getenv("GITHUB_TOKEN", "").strip(),
        github_queries=_split_csv(
            os.getenv(
                "GITHUB_QUERIES",
                "is:open is:issue bounty in:title,body||is:open is:issue reward in:title,body",
            ),
            delimiter="||",
        ),
        rss_sources=_split_csv(os.getenv("RSS_SOURCES")),
        manual_json_sources=_split_csv(os.getenv("MANUAL_JSON_SOURCES")),
        algora_sources=(
            _split_csv(os.getenv("ALGORA_SOURCES"))
            if os.getenv("ALGORA_SOURCES") is not None
            else ["https://algora.io"]
        ),
        immunefi_source=os.getenv("IMMUNEFI_SOURCE", "https://immunefi.com/bug-bounty/").strip(),
        hackerone_source=os.getenv(
            "HACKERONE_SOURCE", "https://www.hackerone.com/bug-bounty-programs"
        ).strip(),
        bugcrowd_source=os.getenv(
            "BUGCROWD_SOURCE", "https://www.bugcrowd.com/bug-bounty-list/"
        ).strip(),
        yeswehack_source=os.getenv("YESWEHACK_SOURCE", "https://yeswehack.com/programs").strip(),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")),
    )
