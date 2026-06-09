from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from bounty_radar_telegram.adapters.base import BaseAdapter
from bounty_radar_telegram.models import Bounty
from bounty_radar_telegram.utils import (
    canonical_url,
    extract_scope_summary,
    infer_difficulty,
    infer_skills,
    now_iso,
    parse_prize,
    stable_hash,
    text_excerpt,
)

logger = logging.getLogger(__name__)


class GitHubIssuesAdapter(BaseAdapter):
    platform = "github"
    search_url = "https://api.github.com/search/issues"
    retry_statuses = {403, 429, 500, 502, 503, 504}
    max_attempts = 4

    def fetch(self) -> list[Bounty]:
        return asyncio.run(self.fetch_async())

    async def fetch_async(self) -> list[Bounty]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"

        timeout = httpx.Timeout(self.settings.request_timeout_seconds)
        async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
            payloads = await asyncio.gather(
                *(self._search(client, query) for query in self.settings.github_queries)
            )

        results: list[Bounty] = []
        for payload in payloads:
            results.extend(self.parse_items(payload.get("items", [])))
        return results

    async def _search(self, client: httpx.AsyncClient, query: str) -> dict[str, Any]:
        if not query.strip():
            return {"items": []}

        params = {"q": query, "sort": "updated", "order": "desc", "per_page": 25}
        for attempt in range(1, self.max_attempts + 1):
            response = await client.get(self.search_url, params=params)
            if response.status_code not in self.retry_statuses:
                response.raise_for_status()
                return response.json()
            if attempt == self.max_attempts:
                response.raise_for_status()
            delay = self._retry_delay(response, attempt)
            logger.warning(
                "GitHub search retry %s/%s for status %s after %.1fs",
                attempt,
                self.max_attempts,
                response.status_code,
                delay,
            )
            await asyncio.sleep(delay)
        return {"items": []}

    def parse_items(self, items: list[dict[str, Any]]) -> list[Bounty]:
        results: list[Bounty] = []
        for item in items:
            if "pull_request" in item:
                continue
            title = item.get("title", "").strip()
            if not title:
                continue
            body = item.get("body", "") or ""
            prize_min, prize_max, currency = parse_prize(f"{title}\n{body}")
            url = item.get("html_url", "")
            results.append(
                Bounty(
                    id=stable_hash(self.platform, url or title),
                    source_id=str(item.get("id", "")),
                    title=title,
                    platform=self.platform,
                    url=canonical_url(url),
                    prize_min=prize_min,
                    prize_max=prize_max,
                    currency=currency,
                    category="oss-bounty",
                    skills=infer_skills(title, body, json.dumps(item.get("labels", []))),
                    difficulty=infer_difficulty(title, body),
                    freshness_date=item.get("created_at") or now_iso(),
                    trust_score=78.0,
                    description=text_excerpt(body, 400),
                    scope_summary=extract_scope_summary(body or title),
                    raw_payload=json.dumps(item, ensure_ascii=True),
                    dedupe_key=canonical_url(url),
                    created_at=now_iso(),
                    updated_at=now_iso(),
                )
            )
        return results

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            return min(float(retry_after), 30.0)
        return min(2.0 ** (attempt - 1), 30.0)
