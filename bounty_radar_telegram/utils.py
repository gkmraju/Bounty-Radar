from __future__ import annotations

import json
import math
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse, urlunparse

SKILL_KEYWORDS = {
    "python": ["python", "fastapi", "django", "flask"],
    "javascript": ["javascript", "typescript", "node", "react", "next.js"],
    "rust": ["rust"],
    "go": ["golang", " go ", "fiber", "gin"],
    "solidity": ["solidity", "smart contract", "evm"],
    "security": ["security", "xss", "ssrf", "sqli", "csrf", "idor", "bug bounty"],
    "devops": ["docker", "kubernetes", "terraform", "aws", "gcp", "azure"],
    "api": ["api", "graphql", "rest"],
    "mobile": ["android", "ios", "mobile", "react native", "flutter"],
}

CURRENCY_SYMBOLS = {
    "$": "USD",
    "usd": "USD",
    "us$": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
}

PRIZE_RANGE_RE = re.compile(
    r"(?P<currency>\$|€|£|usd|eur|gbp|us\$)\s*"
    r"(?P<start>\d[\d,]*(?:\.\d+)?)"
    r"(?:\s*(?:-|to)\s*(?P<currency2>\$|€|£|usd|eur|gbp|us\$)?\s*(?P<end>\d[\d,]*(?:\.\d+)?))?",
    re.IGNORECASE,
)


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    cleaned = value.strip()
    for parser in (
        lambda item: datetime.fromisoformat(item.replace("Z", "+00:00")),
        parsedate_to_datetime,
    ):
        try:
            parsed = parser(cleaned)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except (ValueError, TypeError):
            continue
    return datetime.now(UTC)


def canonical_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def text_excerpt(text: str, max_length: int = 240) -> str:
    compact = re.sub(r"\s+", " ", (text or "")).strip()
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 1].rstrip() + "…"


def extract_scope_summary(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text or "").strip())
    for sentence in sentences:
        snippet = sentence.strip(" -")
        if 20 <= len(snippet) <= 220:
            return snippet
    return text_excerpt(text, 200)


def infer_skills(*parts: str) -> list[str]:
    haystack = " ".join(part.lower() for part in parts if part)
    matched: list[str] = []
    for skill, keywords in SKILL_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            matched.append(skill)
    return matched


def infer_difficulty(*parts: str) -> str:
    haystack = " ".join(part.lower() for part in parts if part)
    if any(token in haystack for token in ("good first issue", "beginner", "easy", "starter")):
        return "beginner"
    if any(token in haystack for token in ("critical", "advanced", "expert", "hard")):
        return "advanced"
    return "intermediate"


def parse_prize(text: str) -> tuple[float | None, float | None, str]:
    if not text:
        return None, None, "USD"
    match = PRIZE_RANGE_RE.search(text)
    if not match:
        return None, None, "USD"
    currency_key = (match.group("currency") or "usd").lower()
    currency = CURRENCY_SYMBOLS.get(currency_key, "USD")
    start = float(match.group("start").replace(",", ""))
    end_raw = match.group("end")
    end = float(end_raw.replace(",", "")) if end_raw else None
    if end is None:
        return start, start, currency
    low, high = sorted((start, end))
    return low, high, currency


def prize_value(prize_min: float | None, prize_max: float | None) -> float:
    if prize_max is not None:
        return prize_max
    if prize_min is not None:
        return prize_min
    return 0.0


def stable_hash(*parts: str) -> str:
    joined = "::".join(part.strip().lower() for part in parts if part)
    return sha256(joined.encode("utf-8")).hexdigest()


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def prize_score(prize_min: float | None, prize_max: float | None) -> float:
    value = max(prize_value(prize_min, prize_max), 0.0)
    if value <= 0:
        return 5.0
    return clamp((math.log10(value + 1) / math.log10(100_000 + 1)) * 100)


def days_old(freshness_date: str) -> int:
    delta = datetime.now(UTC) - parse_datetime(freshness_date)
    return max(0, delta.days)


def freshness_score(freshness_date: str) -> float:
    age = days_old(freshness_date)
    if age <= 2:
        return 100.0
    if age <= 7:
        return 85.0
    if age <= 30:
        return 65.0
    if age <= 90:
        return 40.0
    return 15.0


def difficulty_fit_score(difficulty: str, skills: list[str], preferred_skills: list[str]) -> float:
    base = {"beginner": 72.0, "intermediate": 80.0, "advanced": 62.0}.get(difficulty, 65.0)
    if not preferred_skills:
        return base
    skill_set = {skill.lower() for skill in skills}
    preferred_set = {skill.lower() for skill in preferred_skills}
    overlap = len(skill_set & preferred_set)
    if overlap == 0:
        return clamp(base - 25.0)
    return clamp(base + min(20.0, overlap * 10.0))


def competition_score(platform: str, category: str, skills: list[str], description: str) -> float:
    score = {
        "github": 72.0,
        "algora": 68.0,
        "immunefi": 35.0,
        "hackerone": 32.0,
        "bugcrowd": 34.0,
        "yeswehack": 38.0,
        "rss": 55.0,
        "json": 58.0,
    }.get(platform.lower(), 50.0)
    if category == "freelance-bounty":
        score -= 8.0
    if len(skills) >= 3:
        score += 8.0
    lowered = description.lower()
    if "good first issue" in lowered or "easy win" in lowered:
        score -= 12.0
    if "private repo" in lowered or "invite" in lowered:
        score += 10.0
    return clamp(score)


def load_jsonish(source: str) -> list[dict]:
    payload = json.loads(source)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "bounties", "results", "programs"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def is_local_path(value: str) -> bool:
    return Path(value).exists()
