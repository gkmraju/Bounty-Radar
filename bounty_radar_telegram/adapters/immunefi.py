from __future__ import annotations

import json
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


class ImmunefiAdapter(BaseAdapter):
    platform = "immunefi"
    blocked_titles = {"skip to main content", "learn more"}

    def fetch(self) -> list[Bounty]:
        if not self.settings.immunefi_source:
            return []
        response = self.get(
            self.settings.immunefi_source, headers={"User-Agent": "bounty-radar-telegram/0.1"}
        )
        soup = BeautifulSoup(response.text, "html.parser")
        items: list[Bounty] = []
        seen_urls: set[str] = set()
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "")
            if "/bug-bounty/" not in href or href.rstrip("/") == "/bug-bounty":
                continue
            url = canonical_url(urljoin(self.settings.immunefi_source, href))
            if url in seen_urls:
                continue
            seen_urls.add(url)
            title = anchor.get_text(" ", strip=True)
            if title.lower() in self.blocked_titles:
                continue
            context = anchor.parent.get_text(" ", strip=True) if anchor.parent else title
            prize_min, prize_max, currency = parse_prize(context)
            description = text_excerpt(context, 400)
            items.append(
                Bounty(
                    id=stable_hash(self.platform, url),
                    source_id=stable_hash(title, url),
                    title=title or url.rsplit("/", 1)[-1].replace("-", " ").title(),
                    platform=self.platform,
                    url=url,
                    prize_min=prize_min,
                    prize_max=prize_max,
                    currency=currency,
                    category="bug-bounty",
                    skills=infer_skills(title, context, "web3 smart contract security"),
                    difficulty=infer_difficulty(title, context, "advanced"),
                    freshness_date=now_iso(),
                    trust_score=92.0,
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
