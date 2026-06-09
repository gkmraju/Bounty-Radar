from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import feedparser

from bounty_radar_telegram.adapters.base import BaseAdapter
from bounty_radar_telegram.models import Bounty
from bounty_radar_telegram.utils import (
    canonical_url,
    extract_scope_summary,
    infer_difficulty,
    infer_skills,
    is_local_path,
    load_jsonish,
    now_iso,
    parse_prize,
    stable_hash,
    text_excerpt,
)


class RssAdapter(BaseAdapter):
    platform = "rss"

    def fetch(self) -> list[Bounty]:
        items: list[Bounty] = []
        for source_url in self.settings.rss_sources:
            parsed = feedparser.parse(source_url)
            for entry in parsed.entries:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "") or entry.get("description", "") or ""
                link = canonical_url(entry.get("link", source_url))
                prize_min, prize_max, currency = parse_prize(f"{title}\n{summary}")
                items.append(
                    Bounty(
                        id=stable_hash(self.platform, link or title),
                        source_id=stable_hash(title, link),
                        title=title,
                        platform=self.platform,
                        url=link,
                        prize_min=prize_min,
                        prize_max=prize_max,
                        currency=currency,
                        category="rss-bounty",
                        skills=infer_skills(title, summary),
                        difficulty=infer_difficulty(title, summary),
                        freshness_date=entry.get("published", "")
                        or entry.get("updated", "")
                        or now_iso(),
                        trust_score=66.0,
                        description=text_excerpt(summary, 400),
                        scope_summary=extract_scope_summary(summary or title),
                        raw_payload=json.dumps(entry, ensure_ascii=True, default=str),
                        dedupe_key=link,
                        created_at=now_iso(),
                        updated_at=now_iso(),
                    )
                )
        return items


class ManualJsonAdapter(BaseAdapter):
    platform = "json"

    def fetch(self) -> list[Bounty]:
        items: list[Bounty] = []
        for source in self.settings.manual_json_sources:
            payload = self._load_source(source)
            for record in load_jsonish(payload):
                title = str(record.get("title", "")).strip()
                if not title:
                    continue
                description = str(record.get("description", "") or record.get("scope_summary", ""))
                url = canonical_url(str(record.get("url", "")).strip())
                prize_min = record.get("prize_min")
                prize_max = record.get("prize_max")
                currency = str(record.get("currency", "USD")).upper()
                if prize_min is None and prize_max is None:
                    prize_min, prize_max, currency = parse_prize(f"{title}\n{description}")
                items.append(
                    Bounty(
                        id=record.get("id") or stable_hash(self.platform, url or title),
                        source_id=record.get("source_id", ""),
                        title=title,
                        platform=str(record.get("platform", self.platform)),
                        url=url,
                        prize_min=float(prize_min) if prize_min is not None else None,
                        prize_max=float(prize_max) if prize_max is not None else None,
                        currency=currency,
                        category=str(record.get("category", "manual-bounty")),
                        skills=[str(skill).lower() for skill in record.get("skills", [])],
                        difficulty=str(
                            record.get("difficulty", infer_difficulty(title, description))
                        ),
                        freshness_date=str(record.get("freshness_date", now_iso())),
                        trust_score=float(record.get("trust_score", 60.0)),
                        description=text_excerpt(description, 400),
                        scope_summary=extract_scope_summary(
                            str(record.get("scope_summary", "")) or description or title
                        ),
                        raw_payload=json.dumps(record, ensure_ascii=True),
                        dedupe_key=url or stable_hash(title),
                        created_at=now_iso(),
                        updated_at=now_iso(),
                    )
                )
        return items

    def _load_source(self, source: str) -> str:
        if is_local_path(source):
            return Path(source).read_text(encoding="utf-8")
        if urlparse(source).scheme in {"http", "https"}:
            return self.get(source, headers={"User-Agent": "bounty-radar-telegram/0.1"}).text
        raise ValueError(f"Unsupported manual JSON source: {source}")
