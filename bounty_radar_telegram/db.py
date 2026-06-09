from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from bounty_radar_telegram.models import Bounty, RankBreakdown


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def init(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS bounties (
                    id TEXT PRIMARY KEY,
                    source_id TEXT,
                    title TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    url TEXT NOT NULL,
                    prize_min REAL,
                    prize_max REAL,
                    currency TEXT NOT NULL,
                    category TEXT NOT NULL,
                    skills TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    freshness_date TEXT NOT NULL,
                    trust_score REAL NOT NULL,
                    description TEXT NOT NULL,
                    scope_summary TEXT NOT NULL,
                    competition_score REAL NOT NULL DEFAULT 50,
                    score REAL NOT NULL DEFAULT 0,
                    prize_score REAL NOT NULL DEFAULT 0,
                    difficulty_fit_score REAL NOT NULL DEFAULT 0,
                    freshness_score REAL NOT NULL DEFAULT 0,
                    dedupe_key TEXT NOT NULL,
                    raw_payload TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS publications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bounty_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    message_id TEXT,
                    published_at TEXT NOT NULL,
                    UNIQUE(bounty_id, channel_id)
                );

                CREATE INDEX IF NOT EXISTS idx_bounties_score ON bounties(score DESC);
                CREATE INDEX IF NOT EXISTS idx_bounties_dedupe_key ON bounties(dedupe_key);
                CREATE INDEX IF NOT EXISTS idx_publications_channel ON publications(channel_id);
                """
            )

    def upsert_bounties(self, bounties: list[Bounty]) -> int:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO bounties (
                    id, source_id, title, platform, url, prize_min, prize_max, currency,
                    category, skills, difficulty, freshness_date, trust_score, description,
                    scope_summary, competition_score, score, prize_score, difficulty_fit_score,
                    freshness_score, dedupe_key, raw_payload, created_at, updated_at
                ) VALUES (
                    :id, :source_id, :title, :platform, :url, :prize_min, :prize_max, :currency,
                    :category, :skills, :difficulty, :freshness_date, :trust_score, :description,
                    :scope_summary, :competition_score, :score, :prize_score, :difficulty_fit_score,
                    :freshness_score, :dedupe_key, :raw_payload, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    source_id=excluded.source_id,
                    title=excluded.title,
                    platform=excluded.platform,
                    url=excluded.url,
                    prize_min=excluded.prize_min,
                    prize_max=excluded.prize_max,
                    currency=excluded.currency,
                    category=excluded.category,
                    skills=excluded.skills,
                    difficulty=excluded.difficulty,
                    freshness_date=excluded.freshness_date,
                    trust_score=excluded.trust_score,
                    description=excluded.description,
                    scope_summary=excluded.scope_summary,
                    competition_score=excluded.competition_score,
                    score=excluded.score,
                    prize_score=excluded.prize_score,
                    difficulty_fit_score=excluded.difficulty_fit_score,
                    freshness_score=excluded.freshness_score,
                    dedupe_key=excluded.dedupe_key,
                    raw_payload=excluded.raw_payload,
                    updated_at=excluded.updated_at
                """,
                [self._bounty_params(item) for item in bounties],
            )
        return len(bounties)

    def list_bounties(self) -> list[Bounty]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM bounties ORDER BY score DESC, freshness_date DESC"
            ).fetchall()
        return [self._row_to_bounty(row) for row in rows]

    def update_rankings(self, rankings: list[RankBreakdown]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                UPDATE bounties
                SET prize_score = :prize_score,
                    difficulty_fit_score = :difficulty_fit_score,
                    freshness_score = :freshness_score,
                    competition_score = :competition_score,
                    score = :score
                WHERE id = :bounty_id
                """,
                [asdict(ranking) for ranking in rankings],
            )

    def list_publishable_bounties(
        self, channel_id: str, min_score: float, limit: int
    ) -> list[Bounty]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT b.*
                FROM bounties b
                LEFT JOIN publications p
                  ON p.bounty_id = b.id AND p.channel_id = ?
                WHERE p.id IS NULL
                  AND b.score >= ?
                ORDER BY b.score DESC, b.prize_max DESC, b.freshness_date DESC
                LIMIT ?
                """,
                (channel_id, min_score, limit),
            ).fetchall()
        return [self._row_to_bounty(row) for row in rows]

    def mark_published(
        self,
        bounty_id: str,
        channel_id: str,
        published_at: str,
        message_id: str = "",
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO publications (bounty_id, channel_id, message_id, published_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(bounty_id, channel_id) DO UPDATE SET
                    message_id = excluded.message_id,
                    published_at = excluded.published_at
                """,
                (bounty_id, channel_id, message_id, published_at),
            )

    @staticmethod
    def _bounty_params(bounty: Bounty) -> dict:
        payload = asdict(bounty)
        payload["skills"] = json.dumps(bounty.skills)
        return payload

    @staticmethod
    def _row_to_bounty(row: sqlite3.Row) -> Bounty:
        return Bounty(
            id=row["id"],
            source_id=row["source_id"] or "",
            title=row["title"],
            platform=row["platform"],
            url=row["url"],
            prize_min=row["prize_min"],
            prize_max=row["prize_max"],
            currency=row["currency"],
            category=row["category"],
            skills=json.loads(row["skills"]),
            difficulty=row["difficulty"],
            freshness_date=row["freshness_date"],
            trust_score=row["trust_score"],
            description=row["description"],
            scope_summary=row["scope_summary"],
            competition_score=row["competition_score"],
            score=row["score"],
            prize_score=row["prize_score"],
            difficulty_fit_score=row["difficulty_fit_score"],
            freshness_score=row["freshness_score"],
            dedupe_key=row["dedupe_key"],
            raw_payload=row["raw_payload"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
