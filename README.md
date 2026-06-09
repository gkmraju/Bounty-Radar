# bounty-radar-telegram

`bounty-radar-telegram` fetches code bounties, bug bounties, OSS issue bounties, and freelance-style bounty listings, normalizes them into a common schema, ranks them, stores them in SQLite, and publishes the best results to a Telegram channel.

## Features

- Source adapters for GitHub issue search, Algora-style pages, Immunefi public listings, public program directories, RSS feeds, and manual JSON.
- Shared normalized bounty model:
  `id, title, platform, url, prize_min, prize_max, currency, category, skills, difficulty, freshness_date, trust_score, description, scope_summary`
- Weighted ranking formula:
  `score = prize_score*0.35 + difficulty_fit_score*0.25 + freshness_score*0.15 + trust_score*0.15 + competition_score*0.10`
- URL and title-similarity deduplication.
- SQLite persistence for bounty history and Telegram publication tracking.
- Telegram publishing with repost protection and a responsible disclosure footer on bug bounty posts.

## Folder Structure

```text
.
├── bounty_radar_telegram/
│   ├── adapters/
│   ├── services/
│   ├── cli.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   └── utils.py
├── examples/
│   └── sample_bounties.json
├── .env.example
├── main.py
├── README.md
└── requirements.txt
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Set the required admin config in `.env`:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHANNEL_ID`
- `MAX_RESULTS_PER_RUN`
- `MIN_SCORE`
- `SKILL_FILTERS`
- `BLOCKED_KEYWORDS`

Useful optional source settings:

- `GITHUB_TOKEN`
- `GITHUB_QUERIES` using `||` between queries
- `RSS_SOURCES`
- `MANUAL_JSON_SOURCES`
- `ALGORA_SOURCES`
- `IMMUNEFI_SOURCE`
- `HACKERONE_SOURCE`
- `BUGCROWD_SOURCE`
- `YESWEHACK_SOURCE`

## CLI

```bash
python main.py fetch
python main.py rank
python main.py publish
```

Recommended daily flow:

```bash
python main.py fetch
python main.py rank
python main.py publish
```

## Source Notes

### GitHub issues with bounty keywords

The GitHub adapter uses the public issue search API and parses bounty-like phrases from titles and bodies.

### Algora-style OSS bounties

The Algora adapter supports Next.js-style page data extraction and HTML fallback scraping for public bounty listings.

### Immunefi and public bug bounty programs

The project only summarizes official program scope text already published on source pages. It does not generate exploit steps or attack instructions.

### RSS and manual JSON

Use `RSS_SOURCES` for feed URLs and `MANUAL_JSON_SOURCES` for local JSON files or HTTP endpoints that return a list of bounties or an object with `items`, `bounties`, `results`, or `programs`.

For an offline smoke test:

```bash
set MANUAL_JSON_SOURCES=examples/sample_bounties.json
python main.py fetch
python main.py rank
python main.py publish
```

## Ranking Heuristics

- `prize_score`: logarithmic scaling based on disclosed payout.
- `difficulty_fit_score`: favors configured `SKILL_FILTERS` and manageable difficulty.
- `freshness_score`: rewards recently updated or published opportunities.
- `trust_score`: adapter-specific baseline trust from official/public sources.
- `competition_score`: heuristic estimate of opportunity crowding.

## Storage

The SQLite database is created at `DATABASE_PATH` and stores:

- `bounties`: normalized data plus ranking components.
- `publications`: which bounties have already been posted to a Telegram channel.

## Telegram Publishing

- Sends the top ranked unpublished bounties above `MIN_SCORE`.
- Skips reposts by checking the `publications` table.
- Falls back to preview mode if Telegram credentials are not configured.

## GitHub Actions Schedule

The workflow in `.github/workflows/telegram-alerts.yml` runs daily at `01:30 UTC`, which is `07:00 IST`, and can also be started manually from the Actions tab.

Add these GitHub repository secrets before enabling the schedule:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHANNEL_ID`

Local `.env` aliases `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` are also supported.

Optional GitHub repository variables:

- `MAX_RESULTS_PER_RUN`
- `MIN_SCORE`
- `SKILL_FILTERS`
- `BLOCKED_KEYWORDS`
- `RSS_SOURCES`
- `MANUAL_JSON_SOURCES`
- `GITHUB_QUERIES`

The workflow stores `data/bounty_radar.db` in the GitHub Actions cache so the publication history survives across scheduled runs and the same bounty is not repeatedly posted.
The same SQLite database is uploaded as a short-lived workflow artifact for debugging. It is not committed to the repository.

## Quality And Security Checks

The CI workflow runs on pull requests and pushes to `main`:

- `ruff check .`
- `pytest`
- `bandit -q -r bounty_radar_telegram`

CodeQL runs on pull requests, pushes to `main`, and weekly scheduled scans. Dependabot checks both Python dependencies and GitHub Actions weekly.

## Branch Protection

The repository should protect `main` with pull requests required and direct pushes blocked. This project is configured to work with the following required status checks:

- `Ruff, pytest, and Bandit`
- `Analyze Python`

## Safety

- Only official scope summaries are published.
- No exploit guidance or attack instructions are generated.
- Bug bounty posts include: `Follow platform rules and responsible disclosure.`
