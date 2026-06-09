from __future__ import annotations

import argparse
import logging
import sys

from bounty_radar_telegram.config import load_settings
from bounty_radar_telegram.db import Database
from bounty_radar_telegram.services.fetcher import FetchService
from bounty_radar_telegram.services.publisher import TelegramPublisher
from bounty_radar_telegram.services.ranking import RankingService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounty Radar Telegram publisher")
    parser.add_argument(
        "--log-level", default="INFO", help="Logging level, for example INFO or DEBUG"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("fetch", help="Fetch bounties from configured sources")
    subparsers.add_parser("rank", help="Rank fetched bounties")
    subparsers.add_parser("publish", help="Publish top ranked bounties to Telegram")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    settings = load_settings()
    db = Database(settings.database_path)
    db.init()

    if args.command == "fetch":
        stats = FetchService(settings, db).run()
        print(
            f"Fetched {stats.fetched} items, stored {stats.stored}, "
            f"removed {stats.duplicates_removed} duplicates."
        )
        if stats.adapter_errors:
            print("Adapter warnings:")
            for warning in stats.adapter_errors:
                print(f"- {warning}")
        return 0

    if args.command == "rank":
        rankings = RankingService(settings, db).run()
        print(f"Ranked {len(rankings)} bounties.")
        return 0

    if args.command == "publish":
        results = TelegramPublisher(settings, db).run()
        sent = len([item for item in results if item.sent])
        previews = len([item for item in results if not item.sent])
        print(f"Processed {len(results)} bounties: sent={sent}, previewed={previews}.")
        for item in results[:3]:
            if item.preview:
                print()
                print(item.preview)
        return 0

    parser.print_help()
    return 1
