from __future__ import annotations

import logging

import requests

from bounty_radar_telegram.adapters import (
    AlgoraAdapter,
    GitHubIssuesAdapter,
    ImmunefiAdapter,
    ManualJsonAdapter,
    PublicProgramsAdapter,
    RssAdapter,
)
from bounty_radar_telegram.config import Settings
from bounty_radar_telegram.db import Database
from bounty_radar_telegram.models import FetchStats
from bounty_radar_telegram.services.dedupe import Deduplicator

logger = logging.getLogger(__name__)


class FetchService:
    def __init__(self, settings: Settings, db: Database) -> None:
        self.settings = settings
        self.db = db
        session = requests.Session()
        session.headers.update({"User-Agent": "bounty-radar-telegram/0.1"})
        self.adapters = [
            GitHubIssuesAdapter(settings, session),
            AlgoraAdapter(settings, session),
            ImmunefiAdapter(settings, session),
            PublicProgramsAdapter(settings, session),
            RssAdapter(settings, session),
            ManualJsonAdapter(settings, session),
        ]

    def run(self) -> FetchStats:
        stats = FetchStats()
        all_items = []
        for adapter in self.adapters:
            try:
                items = adapter.fetch()
                logger.info("Fetched %s items from %s", len(items), adapter.__class__.__name__)
                stats.fetched += len(items)
                all_items.extend(items)
            except Exception as exc:  # pragma: no cover - defensive network handling
                message = f"{adapter.__class__.__name__}: {exc}"
                logger.warning("Adapter failed: %s", message)
                stats.adapter_errors.append(message)

        filtered = [
            item
            for item in all_items
            if not any(
                blocked in item.searchable_text() for blocked in self.settings.blocked_keywords
            )
        ]
        deduped, removed = Deduplicator().dedupe(filtered)
        stats.duplicates_removed = removed
        stats.stored = self.db.upsert_bounties(deduped)
        return stats
