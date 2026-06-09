from __future__ import annotations

import requests

from bounty_radar_telegram.db import Database
from bounty_radar_telegram.models import Bounty
from bounty_radar_telegram.services.publisher import TelegramPublisher


class FailingSession:
    def post(self, *args, **kwargs):
        raise requests.Timeout("telegram timeout")


def test_telegram_failure_does_not_mark_published(settings):
    settings.telegram_bot_token = "fake-" + "token"
    settings.telegram_channel_id = "@fake-channel"
    db = Database(settings.database_path)
    db.init()
    db.upsert_bounties(
        [
            Bounty(
                id="pub-1",
                title="Public program bounty",
                platform="json",
                url="https://example.com/program",
                prize_min=1000,
                prize_max=5000,
                currency="USD",
                category="bug-bounty-program",
                skills=["security", "api"],
                difficulty="advanced",
                freshness_date="2026-06-08T00:00:00+00:00",
                trust_score=80,
                description="Official public program with an in-scope API.",
                scope_summary="Official public program scope summary.",
                score=90,
            )
        ]
    )

    publisher = TelegramPublisher(settings, db)
    publisher.session = FailingSession()
    results = publisher.run()
    retryable = db.list_publishable_bounties("@fake-channel", min_score=1, limit=10)

    assert len(results) == 1
    assert results[0].sent is False
    assert "telegram_error" in results[0].message
    assert len(retryable) == 1


def test_telegram_http_error_does_not_expose_bot_token(settings):
    response = requests.Response()
    response.status_code = 400
    response.url = "https://api.telegram.org/botsecret-token/sendMessage"
    response._content = b'{"ok":false,"description":"Bad Request: chat not found"}'
    error = requests.HTTPError("400 Client Error", response=response)

    safe_error = TelegramPublisher._safe_error(error)

    assert "secret-token" not in safe_error
    assert "HTTP 400" in safe_error
    assert "chat not found" in safe_error
