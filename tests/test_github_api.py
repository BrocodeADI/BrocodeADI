"""Tests for GitHub GraphQL client, streak calculations, and language aggregation."""

import datetime
from unittest.mock import MagicMock, patch

from scripts.config import Config
from scripts.github_api import (
    ContributionDay,
    GitHubAPIClient,
    aggregate_languages,
    calculate_streak,
    get_deterministic_utc_window,
)


def test_deterministic_utc_window():
    from_dt, to_dt = get_deterministic_utc_window(365)
    assert from_dt.tzinfo == datetime.timezone.utc
    assert to_dt.tzinfo == datetime.timezone.utc
    assert from_dt.hour == 0 and from_dt.minute == 0 and from_dt.second == 0
    assert to_dt.hour == 23 and to_dt.minute == 59 and to_dt.second == 59
    delta = to_dt - from_dt
    assert delta.days == 364  # 365 calendar days inclusive


def test_streak_calculation():
    days = [
        ContributionDay("2026-01-01", 0, "", 4),
        ContributionDay("2026-01-02", 3, "", 5),
        ContributionDay("2026-01-03", 5, "", 6),
        ContributionDay("2026-01-04", 2, "", 0),
        ContributionDay("2026-01-05", 0, "", 1),
        ContributionDay("2026-01-06", 1, "", 2),
        ContributionDay("2026-01-07", 4, "", 3),
    ]
    streak = calculate_streak(days)
    assert streak.longest_streak == 3
    assert streak.longest_start == "2026-01-02"
    assert streak.longest_end == "2026-01-04"
    assert streak.current_streak == 2
    assert streak.current_start == "2026-01-06"
    assert streak.current_end == "2026-01-07"
    assert streak.total_active_days == 5
    assert streak.total_days == 7


def test_empty_streak():
    streak = calculate_streak([])
    assert streak.current_streak == 0
    assert streak.longest_streak == 0
    assert streak.total_active_days == 0


def test_language_aggregation():
    mock_repos = [
        {
            "name": "repo1",
            "isFork": False,
            "isPrivate": False,
            "languages": {
                "edges": [
                    {"size": 800, "node": {"name": "Python", "color": "#3572A5"}},
                    {"size": 200, "node": {"name": "Rust", "color": "#dea584"}}
                ]
            }
        },
        {
            "name": "repo2-fork",
            "isFork": True,  # Fork should be excluded
            "isPrivate": False,
            "languages": {
                "edges": [
                    {"size": 50000, "node": {"name": "Java", "color": "#b07219"}}
                ]
            }
        },
        {
            "name": "repo3",
            "isFork": False,
            "isPrivate": False,
            "languages": {
                "edges": [
                    {"size": 200, "node": {"name": "Rust", "color": "#dea584"}}
                ]
            }
        }
    ]

    stats = aggregate_languages(mock_repos)
    assert len(stats) == 2
    # Total: Python = 800 (66.67%), Rust = 400 (33.33%)
    assert stats[0].name == "Python"
    assert stats[0].bytes == 800
    assert stats[0].percentage == 66.67
    assert stats[1].name == "Rust"
    assert stats[1].bytes == 400
    assert stats[1].percentage == 33.33


def test_github_api_fallback_on_error():
    cfg = Config(github_token="fake_token")
    client = GitHubAPIClient(cfg)
    
    with patch("requests.post") as mock_post:
        mock_post.side_effect = Exception("Connection timeout")
        user_data = client.fetch_user_data()
        assert user_data.username == cfg.github_username
        assert user_data.total_contributions > 0
        assert len(user_data.weeks) > 0
