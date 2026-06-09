from __future__ import annotations

from pathlib import Path

import pytest

from bounty_radar_telegram.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        telegram_bot_token="",
        telegram_channel_id="",
        max_results_per_run=10,
        min_score=1.0,
        skill_filters=["python", "security", "api"],
        blocked_keywords=[],
        database_path=tmp_path / "bounty_radar.db",
        github_token="",
        github_queries=["is:open is:issue bounty"],
        rss_sources=[],
        manual_json_sources=[],
        algora_sources=[],
        immunefi_source="",
        hackerone_source="",
        bugcrowd_source="",
        yeswehack_source="",
        request_timeout_seconds=5,
    )
