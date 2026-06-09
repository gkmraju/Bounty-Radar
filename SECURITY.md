# Security

## Secrets

Never commit `.env`, Telegram bot tokens, Telegram channel IDs, private API tokens, SQLite databases, or downloaded source data. Store production values in GitHub repository secrets and variables:

- `TELEGRAM_BOT_TOKEN` as a GitHub Actions secret.
- `TELEGRAM_CHANNEL_ID` as a GitHub Actions secret.
- Optional tuning values such as `MAX_RESULTS_PER_RUN`, `MIN_SCORE`, `SKILL_FILTERS`, `BLOCKED_KEYWORDS`, `RSS_SOURCES`, and `MANUAL_JSON_SOURCES` as GitHub Actions variables.

Runtime SQLite history is stored in GitHub Actions cache and uploaded as a short-lived artifact for diagnostics. It is not committed to the repository.

## Publishing Safety

Bug bounty posts must only summarize official public scope and must not include exploit steps, payloads, or attack instructions. Telegram posts for bug bounty categories include a responsible disclosure reminder.

## Source Safety

Manual JSON and RSS sources are admin-controlled inputs. Only add sources you trust, and prefer official bounty, program, or project URLs.
