from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

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


@dataclass(slots=True)
class ProgramSource:
    platform: str
    url: str
    trust_score: float


class PublicProgramsAdapter(BaseAdapter):
    platform = "public-programs"
    blocked_titles = {
        "skip to main content",
        "sign in",
        "log in",
        "learn more",
        "contact us",
        "programs",
    }
    blocked_path_tokens = ("login", "signin", "signup", "contact", "about", "blog", "privacy")

    def fetch(self) -> list[Bounty]:
        sources = [
            ProgramSource("hackerone", self.settings.hackerone_source, 89.0),
            ProgramSource("bugcrowd", self.settings.bugcrowd_source, 87.0),
            ProgramSource("yeswehack", self.settings.yeswehack_source, 84.0),
        ]
        items: list[Bounty] = []
        for source in sources:
            if not source.url:
                continue
            response = self.get(source.url, headers={"User-Agent": "bounty-radar-telegram/0.1"})
            items.extend(self._parse_program_cards(source, response.text))
        return items

    def _parse_program_cards(self, source: ProgramSource, html: str) -> list[Bounty]:
        soup = BeautifulSoup(html, "html.parser")
        base_host = urlparse(source.url).netloc
        items: list[Bounty] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "")
            title = anchor.get_text(" ", strip=True)
            if len(title) < 4:
                continue
            if title.lower() in self.blocked_titles:
                continue
            url = canonical_url(urljoin(source.url, href))
            parsed = urlparse(url)
            if parsed.netloc != base_host:
                continue
            if any(token in parsed.path.lower() for token in self.blocked_path_tokens):
                continue
            if url in seen:
                continue
            context = anchor.parent.get_text(" ", strip=True) if anchor.parent else title
            lowered = context.lower()
            if not any(token in lowered for token in ("bounty", "reward", "program", "scope")):
                continue
            if len(context) < 30:
                continue
            seen.add(url)
            prize_min, prize_max, currency = parse_prize(context)
            description = text_excerpt(context, 350)
            items.append(
                Bounty(
                    id=stable_hash(source.platform, url),
                    source_id=stable_hash(title, url),
                    title=title,
                    platform=source.platform,
                    url=url,
                    prize_min=prize_min,
                    prize_max=prize_max,
                    currency=currency,
                    category="bug-bounty-program",
                    skills=infer_skills(title, context, "security"),
                    difficulty=infer_difficulty(title, context),
                    freshness_date=now_iso(),
                    trust_score=source.trust_score,
                    description=description,
                    scope_summary=extract_scope_summary(description or title),
                    raw_payload=json.dumps(
                        {"title": title, "url": url, "context": context}, ensure_ascii=True
                    ),
                    dedupe_key=url,
                    created_at=now_iso(),
                    updated_at=now_iso(),
                )
            )
        return items
