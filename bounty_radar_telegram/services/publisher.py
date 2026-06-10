from __future__ import annotations

import logging

import requests
from requests import RequestException

from bounty_radar_telegram.config import Settings
from bounty_radar_telegram.db import Database
from bounty_radar_telegram.models import Bounty, PublishResult
from bounty_radar_telegram.utils import now_iso, text_excerpt

logger = logging.getLogger(__name__)


class TelegramPublisher:
    send_message_url = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, settings: Settings, db: Database) -> None:
        self.settings = settings
        self.db = db
        self.session = requests.Session()

    def run(self) -> list[PublishResult]:
        bounties = self.db.list_publishable_bounties(
            channel_id=self.settings.telegram_channel_id or "dry-run",
            min_score=self.settings.min_score,
            limit=self.settings.max_results_per_run,
        )
        results: list[PublishResult] = []
        for bounty in bounties:
            message = self.format_message(bounty)
            if not self.settings.telegram_bot_token or not self.settings.telegram_channel_id:
                logger.info(
                    "Telegram config missing, previewing instead of sending: %s", bounty.title
                )
                results.append(
                    PublishResult(
                        bounty_id=bounty.id,
                        sent=False,
                        message="preview",
                        preview=message,
                    )
                )
                continue
            try:
                payload = self._send_message(message)
            except RequestException as exc:
                safe_error = self._safe_error(exc)
                logger.warning("Telegram send failed for %s: %s", bounty.id, safe_error)
                results.append(
                    PublishResult(
                        bounty_id=bounty.id,
                        sent=False,
                        message=f"telegram_error: {safe_error}",
                        preview=message,
                    )
                )
                continue
            message_id = str(payload.get("result", {}).get("message_id", ""))
            self.db.mark_published(
                bounty_id=bounty.id,
                channel_id=self.settings.telegram_channel_id,
                published_at=now_iso(),
                message_id=message_id,
            )
            results.append(
                PublishResult(
                    bounty_id=bounty.id,
                    sent=True,
                    message="sent",
                    message_id=message_id,
                    preview=message,
                )
            )
        return results

    def _send_message(self, message: str) -> dict:
        response = self.session.post(
            self.send_message_url.format(token=self.settings.telegram_bot_token),
            json={
                "chat_id": self.settings.telegram_channel_id,
                "text": message,
                "disable_web_page_preview": False,
            },
            timeout=self.settings.request_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _safe_error(exc: RequestException) -> str:
        response = getattr(exc, "response", None)
        if response is None:
            return exc.__class__.__name__
        description = ""
        try:
            payload = response.json()
            description = str(payload.get("description", ""))
        except ValueError:
            description = response.reason or ""
        suffix = f": {description}" if description else ""
        return f"HTTP {response.status_code}{suffix}"

    @staticmethod
    def format_message(bounty: Bounty) -> str:
        difficulty_emoji = {
            "beginner": "\U0001f7e2",
            "intermediate": "\U0001f7e1",
            "advanced": "\U0001f534",
        }.get(bounty.difficulty, "\U0001f7e1")
        lines = [
            f"\U0001f3af {bounty.title}",
            f"\U0001f4b0 Prize: {bounty.display_prize}",
            f"{difficulty_emoji} Difficulty: {bounty.difficulty.title()}",
            f"\u2b50 Score: {bounty.score:.2f}",
            f"\U0001f3e2 Platform: {bounty.platform.title()}",
        ]
        if bounty.skills:
            lines.append(f"\U0001f6e0 Skills: {', '.join(bounty.skills[:5])}")
        lines.append(f"\U0001f9ed Scope: {text_excerpt(bounty.scope_summary, 200)}")
        lines.append(f"\U0001f517 Official link: {bounty.url}")
        if bounty.category.startswith("bug-bounty"):
            lines.append("\u26a0\ufe0f Follow platform rules and responsible disclosure.")
        return "\n".join(lines)
