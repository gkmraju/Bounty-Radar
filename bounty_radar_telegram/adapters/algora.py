from __future__ import annotations

import json
from collections.abc import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

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


class AlgoraAdapter(BaseAdapter):
    platform = "algora"

    def fetch(self) -> list[Bounty]:
        results: list[Bounty] = []
        for source_url in self.settings.algora_sources:
            response = self.get(source_url, headers={"User-Agent": "bounty-radar-telegram/0.1"})
            html = response.text
            results.extend(self._from_next_data(html, source_url))
            if results:
                continue
            results.extend(self._from_links(html, source_url))
        return results

    def _from_next_data(self, html: str, base_url: str) -> list[Bounty]:
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            return []
        try:
            payload = json.loads(script.string)
        except json.JSONDecodeError:
            return []

        items: list[Bounty] = []
        for record in self._walk(payload):
            if not isinstance(record, dict):
                continue
            title = record.get("title") or record.get("name")
            href = record.get("url") or record.get("href")
            if not title or not href:
                continue
            description = record.get("description") or record.get("summary") or ""
            prize_min, prize_max, currency = parse_prize(
                f"{record.get('amount', '')} {record.get('reward', '')} {description}"
            )
            url = canonical_url(urljoin(base_url, href))
            items.append(
                Bounty(
                    id=stable_hash(self.platform, url),
                    source_id=stable_hash(title, url),
                    title=title.strip(),
                    platform=self.platform,
                    url=url,
                    prize_min=prize_min,
                    prize_max=prize_max,
                    currency=currency,
                    category="oss-bounty",
                    skills=infer_skills(title, description),
                    difficulty=infer_difficulty(title, description),
                    freshness_date=record.get("createdAt")
                    or record.get("publishedAt")
                    or now_iso(),
                    trust_score=74.0,
                    description=text_excerpt(description, 400),
                    scope_summary=extract_scope_summary(description or title),
                    raw_payload=json.dumps(record, ensure_ascii=True),
                    dedupe_key=url,
                    created_at=now_iso(),
                    updated_at=now_iso(),
                )
            )
        return items

    def _from_links(self, html: str, base_url: str) -> list[Bounty]:
        soup = BeautifulSoup(html, "html.parser")
        items: list[Bounty] = []
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "")
            title = anchor.get_text(" ", strip=True)
            surrounding = anchor.parent.get_text(" ", strip=True) if anchor.parent else title
            if "bounty" not in surrounding.lower() and "reward" not in surrounding.lower():
                continue
            if len(title) < 6:
                continue
            prize_min, prize_max, currency = parse_prize(surrounding)
            url = canonical_url(urljoin(base_url, href))
            items.append(
                Bounty(
                    id=stable_hash(self.platform, url),
                    source_id=stable_hash(title, url),
                    title=title,
                    platform=self.platform,
                    url=url,
                    prize_min=prize_min,
                    prize_max=prize_max,
                    currency=currency,
                    category="oss-bounty",
                    skills=infer_skills(title, surrounding),
                    difficulty=infer_difficulty(title, surrounding),
                    freshness_date=now_iso(),
                    trust_score=72.0,
                    description=text_excerpt(surrounding, 400),
                    scope_summary=extract_scope_summary(surrounding or title),
                    raw_payload="",
                    dedupe_key=url,
                    created_at=now_iso(),
                    updated_at=now_iso(),
                )
            )
        return items

    def _walk(self, value: object) -> Iterable[object]:
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from self._walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from self._walk(child)
