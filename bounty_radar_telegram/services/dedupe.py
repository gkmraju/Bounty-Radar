from __future__ import annotations

from difflib import SequenceMatcher

from bounty_radar_telegram.models import Bounty
from bounty_radar_telegram.utils import canonical_url, normalize_title, stable_hash


class Deduplicator:
    def dedupe(self, items: list[Bounty]) -> tuple[list[Bounty], int]:
        deduped: list[Bounty] = []
        removed = 0
        for item in sorted(items, key=self._sort_key, reverse=True):
            duplicate = self._find_duplicate(item, deduped)
            if duplicate is None:
                item.dedupe_key = (
                    item.dedupe_key or canonical_url(item.url) or stable_hash(item.title)
                )
                deduped.append(item)
                continue
            removed += 1
            self._merge(duplicate, item)
        return deduped, removed

    def _find_duplicate(self, candidate: Bounty, accepted: list[Bounty]) -> Bounty | None:
        candidate_url = canonical_url(candidate.url)
        candidate_title = normalize_title(candidate.title)
        for current in accepted:
            if candidate_url and candidate_url == canonical_url(current.url):
                return current
            similarity = SequenceMatcher(
                None, candidate_title, normalize_title(current.title)
            ).ratio()
            if similarity >= 0.92:
                return current
        return None

    @staticmethod
    def _sort_key(item: Bounty) -> tuple[float, float, int]:
        prize = item.prize_max or item.prize_min or 0.0
        return (item.trust_score, prize, len(item.description))

    @staticmethod
    def _merge(primary: Bounty, duplicate: Bounty) -> None:
        if len(duplicate.description) > len(primary.description):
            primary.description = duplicate.description
        if len(duplicate.scope_summary) > len(primary.scope_summary):
            primary.scope_summary = duplicate.scope_summary
        if (duplicate.prize_max or 0.0) > (primary.prize_max or 0.0):
            primary.prize_max = duplicate.prize_max
            primary.prize_min = duplicate.prize_min
            primary.currency = duplicate.currency
        primary.skills = sorted(set(primary.skills) | set(duplicate.skills))
        primary.trust_score = max(primary.trust_score, duplicate.trust_score)
