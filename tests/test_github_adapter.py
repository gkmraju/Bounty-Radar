from __future__ import annotations

from bounty_radar_telegram.adapters.github import GitHubIssuesAdapter


def test_github_parser_normalizes_issue_bounty(settings):
    adapter = GitHubIssuesAdapter(settings)
    bounties = adapter.parse_items(
        [
            {
                "id": 123,
                "title": "[$750 bounty] Add FastAPI webhook retries",
                "body": "Reward: $250 to $750. Official issue scope only.",
                "html_url": "https://github.com/acme/project/issues/42",
                "created_at": "2026-06-08T12:00:00Z",
                "labels": [{"name": "python"}, {"name": "api"}],
            },
            {
                "id": 124,
                "title": "Ignore pull request result",
                "body": "Not a bounty.",
                "html_url": "https://github.com/acme/project/pull/43",
                "pull_request": {},
            },
        ]
    )

    assert len(bounties) == 1
    bounty = bounties[0]
    assert bounty.platform == "github"
    assert bounty.prize_min == 750
    assert bounty.prize_max == 750
    assert bounty.currency == "USD"
    assert "python" in bounty.skills
    assert "api" in bounty.skills
    assert bounty.category == "oss-bounty"
    assert bounty.url == "https://github.com/acme/project/issues/42"


def test_github_retry_delay_honors_retry_after(settings):
    import httpx

    adapter = GitHubIssuesAdapter(settings)
    response = httpx.Response(429, headers={"Retry-After": "9"})

    assert adapter._retry_delay(response, attempt=1) == 9.0
